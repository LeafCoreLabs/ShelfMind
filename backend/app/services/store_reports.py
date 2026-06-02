"""Query store database and build structured reports for the AI assistant."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commerce import Customer, Invoice, Payment, PurchaseOrder, Vendor
from app.models.store import Product, Transaction


@dataclass
class ReportParams:
    report_type: str = "overview"
    period: str = "week"  # today | week | month | year | all
    days: int | None = None
    limit: int = 15
    category: str | None = None
    customer_id: int | None = None
    customer_name: str | None = None


def _period_start(period: str, days: int | None = None) -> datetime | None:
    now = datetime.now(timezone.utc)
    if period == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        return now - timedelta(days=7)
    if period == "month":
        return now - timedelta(days=30)
    if period == "year":
        return now - timedelta(days=365)
    if period == "all":
        return None
    if days and days > 0:
        return now - timedelta(days=days)
    return now - timedelta(days=7)


def parse_report_params(message: str, params: dict | None = None) -> ReportParams:
    """Infer report type and period from LLM params or user message."""
    params = params or {}
    m = message.lower()

    report_type = (params.get("report_type") or params.get("type") or "").lower().replace("-", "_")
    if not report_type:
        if any(w in m for w in ["inventory report", "stock report", "inventory status"]):
            report_type = "inventory"
        elif any(w in m for w in ["sales report", "sales summary", "revenue report"]):
            report_type = "sales"
        elif any(w in m for w in ["top seller", "best seller", "top product", "most sold"]):
            report_type = "top_products"
        elif any(w in m for w in ["customer report", "regulars report", "top customer"]):
            report_type = "customers"
        elif any(w in m for w in ["invoice report", "billing report", "unpaid report"]):
            report_type = "invoices"
        elif any(w in m for w in ["category report", "category sales", "by category"]):
            report_type = "categories"
        elif any(w in m for w in ["purchase report", "po report", "vendor order"]):
            report_type = "purchases"
        elif any(w in m for w in ["gst report", "tax report", "gst summary"]):
            report_type = "gst"
        elif any(w in m for w in ["store summary", "business summary", "overview report", "full report"]):
            report_type = "overview"
        elif "report" in m:
            report_type = "overview"
        else:
            report_type = "overview"

    period = (params.get("period") or "").lower()
    if not period:
        if "today" in m:
            period = "today"
        elif any(w in m for w in ["this month", "last month", "monthly", "past month"]):
            period = "month"
        elif any(w in m for w in ["this year", "yearly", "annual"]):
            period = "year"
        elif any(w in m for w in ["all time", "overall", "total"]):
            period = "all"
        elif "week" in m:
            period = "week"
        else:
            period = "week"

    days = params.get("days")
    if days is None:
        dm = re.search(r"(?:last|past)\s+(\d+)\s+days?", m)
        if dm:
            days = int(dm.group(1))
            period = "custom"
    elif isinstance(days, str) and days.isdigit():
        days = int(days)

    limit = params.get("limit") or 15
    try:
        limit = min(50, max(5, int(limit)))
    except (TypeError, ValueError):
        limit = 15

    customer_id = params.get("customer_id")
    if customer_id:
        try:
            customer_id = int(customer_id)
        except (TypeError, ValueError):
            customer_id = None

    return ReportParams(
        report_type=report_type,
        period=period,
        days=days if period == "custom" else None,
        limit=limit,
        category=(params.get("category") or "").strip() or None,
        customer_id=customer_id,
        customer_name=(params.get("customer_name") or "").strip() or None,
    )


def _period_label(rp: ReportParams) -> str:
    if rp.period == "today":
        return "today"
    if rp.period == "week":
        return "the last 7 days"
    if rp.period == "month":
        return "the last 30 days"
    if rp.period == "year":
        return "the last 12 months"
    if rp.period == "all":
        return "all time"
    if rp.days:
        return f"the last {rp.days} days"
    return "the last 7 days"


async def _sales_report(db: AsyncSession, store_id: int, rp: ReportParams) -> dict:
    since = _period_start(rp.period, rp.days)
    q = select(
        func.count(Transaction.id),
        func.coalesce(func.sum(Transaction.quantity * Transaction.unit_price), 0),
        func.coalesce(func.sum(Transaction.quantity), 0),
    ).where(Transaction.store_id == store_id)
    if since:
        q = q.where(Transaction.sold_at >= since)
    if rp.customer_id:
        q = q.where(Transaction.customer_id == rp.customer_id)
    count, revenue, units = (await db.execute(q)).one()

    day_col = func.date_trunc("day", Transaction.sold_at)
    daily_q = (
        select(
            day_col.label("day"),
            func.count(Transaction.id).label("txns"),
            func.coalesce(func.sum(Transaction.quantity * Transaction.unit_price), 0).label("revenue"),
        )
        .where(Transaction.store_id == store_id)
        .group_by(day_col)
        .order_by(day_col.desc())
        .limit(rp.limit)
    )
    if since:
        daily_q = daily_q.where(Transaction.sold_at >= since)
    daily_rows = (await db.execute(daily_q)).all()
    rows = [
        {
            "date": str(r.day.date()) if r.day else "",
            "transactions": int(r.txns),
            "revenue": round(float(r.revenue), 2),
        }
        for r in daily_rows
    ]

    label = _period_label(rp)
    return {
        "report_type": "sales",
        "title": f"Sales report — {label}",
        "summary": f"{int(count)} transactions, {int(units)} units sold, Rs {float(revenue):,.2f} revenue {label}.",
        "metrics": {
            "transactions": int(count),
            "units_sold": int(units),
            "revenue": round(float(revenue), 2),
            "period": label,
        },
        "rows": rows,
    }


async def _inventory_report(db: AsyncSession, store_id: int, rp: ReportParams) -> dict:
    q = select(Product).where(Product.store_id == store_id).order_by(Product.stock_on_hand)
    if rp.category:
        q = q.where(Product.category.ilike(f"%{rp.category}%"))
    products = (await db.execute(q)).scalars().all()
    low = [p for p in products if p.stock_on_hand <= p.reorder_level]
    rows = [
        {
            "product": p.name,
            "category": p.category,
            "stock": p.stock_on_hand,
            "reorder_level": p.reorder_level,
            "status": "low" if p.stock_on_hand <= p.reorder_level else "ok",
            "value": round(p.stock_on_hand * p.list_price, 2),
        }
        for p in products[: rp.limit]
    ]
    total_value = sum(p.stock_on_hand * p.list_price for p in products)
    return {
        "report_type": "inventory",
        "title": "Inventory report",
        "summary": f"{len(products)} products in catalog, {len(low)} below reorder level, stock value Rs {total_value:,.2f}.",
        "metrics": {"products": len(products), "low_stock": len(low), "stock_value": round(total_value, 2)},
        "rows": rows,
    }


async def _top_products_report(db: AsyncSession, store_id: int, rp: ReportParams) -> dict:
    since = _period_start(rp.period, rp.days)
    q = (
        select(
            Product.name,
            Product.category,
            func.sum(Transaction.quantity).label("qty"),
            func.coalesce(func.sum(Transaction.quantity * Transaction.unit_price), 0).label("revenue"),
        )
        .join(Product, Product.id == Transaction.product_id)
        .where(Transaction.store_id == store_id)
        .group_by(Product.id, Product.name, Product.category)
        .order_by(func.sum(Transaction.quantity * Transaction.unit_price).desc())
        .limit(rp.limit)
    )
    if since:
        q = q.where(Transaction.sold_at >= since)
    rows_raw = (await db.execute(q)).all()
    rows = [
        {"product": r.name, "category": r.category, "quantity": int(r.qty), "revenue": round(float(r.revenue), 2)}
        for r in rows_raw
    ]
    label = _period_label(rp)
    top = rows[0]["product"] if rows else "—"
    return {
        "report_type": "top_products",
        "title": f"Top products — {label}",
        "summary": f"Top seller: {top}. Showing {len(rows)} products by revenue {label}.",
        "metrics": {"period": label, "count": len(rows)},
        "rows": rows,
    }


async def _customers_report(db: AsyncSession, store_id: int, rp: ReportParams) -> dict:
    q = select(Customer).where(Customer.store_id == store_id).order_by(Customer.total_spent.desc()).limit(rp.limit)
    customers = (await db.execute(q)).scalars().all()
    rows = [
        {
            "customer": c.name,
            "segment": c.segment,
            "total_spent": round(float(c.total_spent), 2),
            "last_purchase": c.last_purchase_at.strftime("%Y-%m-%d") if c.last_purchase_at else "—",
        }
        for c in customers
    ]
    total = sum(c.total_spent for c in customers)
    return {
        "report_type": "customers",
        "title": "Customer report",
        "summary": f"{len(customers)} customers listed. Top spenders total Rs {total:,.2f}.",
        "metrics": {"customers": len(customers), "listed_revenue": round(total, 2)},
        "rows": rows,
    }


async def _invoices_report(db: AsyncSession, store_id: int, rp: ReportParams) -> dict:
    since = _period_start(rp.period, rp.days)
    q = select(Invoice).where(Invoice.store_id == store_id).order_by(Invoice.issued_at.desc()).limit(rp.limit)
    if since:
        q = q.where(Invoice.issued_at >= since)
    invoices = (await db.execute(q)).scalars().all()
    unpaid = [i for i in invoices if i.status in ("sent", "overdue", "draft")]
    rows = [
        {
            "invoice": inv.invoice_number,
            "status": inv.status,
            "total": round(float(inv.total), 2),
            "issued": inv.issued_at.strftime("%Y-%m-%d") if inv.issued_at else "",
        }
        for inv in invoices
    ]
    label = _period_label(rp)
    due = sum(i.total for i in unpaid)
    return {
        "report_type": "invoices",
        "title": f"Invoice report — {label}",
        "summary": f"{len(invoices)} invoices, {len(unpaid)} unpaid (Rs {due:,.2f} outstanding) {label}.",
        "metrics": {"invoices": len(invoices), "unpaid": len(unpaid), "outstanding": round(due, 2)},
        "rows": rows,
    }


async def _categories_report(db: AsyncSession, store_id: int, rp: ReportParams) -> dict:
    since = _period_start(rp.period, rp.days)
    q = (
        select(
            Product.category,
            func.sum(Transaction.quantity).label("qty"),
            func.coalesce(func.sum(Transaction.quantity * Transaction.unit_price), 0).label("revenue"),
        )
        .join(Product, Product.id == Transaction.product_id)
        .where(Transaction.store_id == store_id)
        .group_by(Product.category)
        .order_by(func.sum(Transaction.quantity * Transaction.unit_price).desc())
    )
    if since:
        q = q.where(Transaction.sold_at >= since)
    rows_raw = (await db.execute(q)).all()
    rows = [
        {"category": r.category, "quantity": int(r.qty), "revenue": round(float(r.revenue), 2)}
        for r in rows_raw
    ]
    label = _period_label(rp)
    top = rows[0]["category"] if rows else "—"
    return {
        "report_type": "categories",
        "title": f"Category sales — {label}",
        "summary": f"Top category: {top}. {len(rows)} categories with sales {label}.",
        "metrics": {"period": label, "categories": len(rows)},
        "rows": rows,
    }


async def _purchases_report(db: AsyncSession, store_id: int, rp: ReportParams) -> dict:
    since = _period_start(rp.period, rp.days)
    q = (
        select(PurchaseOrder, Vendor.name)
        .join(Vendor, Vendor.id == PurchaseOrder.vendor_id)
        .where(PurchaseOrder.store_id == store_id)
        .order_by(PurchaseOrder.ordered_at.desc())
        .limit(rp.limit)
    )
    if since:
        q = q.where(PurchaseOrder.ordered_at >= since)
    rows_raw = (await db.execute(q)).all()
    rows = [
        {
            "po_id": po.id,
            "vendor": vname,
            "status": po.status,
            "total": round(float(po.total), 2),
            "ordered": po.ordered_at.strftime("%Y-%m-%d") if po.ordered_at else "",
        }
        for po, vname in rows_raw
    ]
    pending = sum(1 for po, _ in rows_raw if po.status != "received")
    label = _period_label(rp)
    return {
        "report_type": "purchases",
        "title": f"Purchase orders — {label}",
        "summary": f"{len(rows)} purchase orders, {pending} not yet received {label}.",
        "metrics": {"orders": len(rows), "pending": pending},
        "rows": rows,
    }


async def _gst_report(db: AsyncSession, store_id: int, rp: ReportParams) -> dict:
    since = _period_start(rp.period, rp.days)
    q = select(
        func.coalesce(func.sum(Invoice.subtotal), 0),
        func.coalesce(func.sum(Invoice.tax_amount), 0),
        func.coalesce(func.sum(Invoice.cgst_amount), 0),
        func.coalesce(func.sum(Invoice.sgst_amount), 0),
        func.coalesce(func.sum(Invoice.total), 0),
        func.count(Invoice.id),
    ).where(Invoice.store_id == store_id)
    if since:
        q = q.where(Invoice.issued_at >= since)
    subtotal, tax, cgst, sgst, total, count = (await db.execute(q)).one()
    label = _period_label(rp)
    return {
        "report_type": "gst",
        "title": f"GST summary — {label}",
        "summary": f"{int(count)} invoices: subtotal Rs {float(subtotal):,.2f}, GST Rs {float(tax):,.2f}, total Rs {float(total):,.2f} {label}.",
        "metrics": {
            "invoices": int(count),
            "subtotal": round(float(subtotal), 2),
            "gst": round(float(tax), 2),
            "cgst": round(float(cgst), 2),
            "sgst": round(float(sgst), 2),
            "total": round(float(total), 2),
        },
        "rows": [
            {"component": "Taxable value", "amount": round(float(subtotal), 2)},
            {"component": "CGST", "amount": round(float(cgst), 2)},
            {"component": "SGST", "amount": round(float(sgst), 2)},
            {"component": "Total GST", "amount": round(float(tax), 2)},
            {"component": "Invoice total", "amount": round(float(total), 2)},
        ],
    }


async def _overview_report(db: AsyncSession, store_id: int, rp: ReportParams) -> dict:
    since = _period_start(rp.period, rp.days)
    sales_q = select(
        func.count(Transaction.id),
        func.coalesce(func.sum(Transaction.quantity * Transaction.unit_price), 0),
    ).where(Transaction.store_id == store_id)
    if since:
        sales_q = sales_q.where(Transaction.sold_at >= since)
    tx_count, revenue = (await db.execute(sales_q)).one()

    product_count = (
        await db.execute(select(func.count(Product.id)).where(Product.store_id == store_id))
    ).scalar() or 0
    low_stock = (
        await db.execute(
            select(func.count(Product.id)).where(
                Product.store_id == store_id, Product.stock_on_hand <= Product.reorder_level
            )
        )
    ).scalar() or 0
    customer_count = (
        await db.execute(select(func.count(Customer.id)).where(Customer.store_id == store_id))
    ).scalar() or 0
    unpaid = (
        await db.execute(
            select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.total), 0)).where(
                Invoice.store_id == store_id, Invoice.status.in_(["sent", "overdue", "draft"])
            )
        )
    ).one()
    payments_total = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Invoice, Invoice.id == Payment.invoice_id)
            .where(Invoice.store_id == store_id)
        )
    ).scalar() or 0

    label = _period_label(rp)
    rows = [
        {"metric": "Sales transactions", "value": int(tx_count)},
        {"metric": "Revenue", "value": round(float(revenue), 2)},
        {"metric": "Products in catalog", "value": int(product_count)},
        {"metric": "Low stock items", "value": int(low_stock)},
        {"metric": "Customers", "value": int(customer_count)},
        {"metric": "Unpaid invoices", "value": int(unpaid[0])},
        {"metric": "Outstanding amount", "value": round(float(unpaid[1]), 2)},
        {"metric": "Payments collected", "value": round(float(payments_total), 2)},
    ]
    return {
        "report_type": "overview",
        "title": f"Store overview — {label}",
        "summary": (
            f"Rs {float(revenue):,.2f} revenue from {int(tx_count)} sales {label}. "
            f"{int(low_stock)} items low on stock, {int(unpaid[0])} unpaid bills."
        ),
        "metrics": {
            "revenue": round(float(revenue), 2),
            "transactions": int(tx_count),
            "low_stock": int(low_stock),
            "unpaid_invoices": int(unpaid[0]),
        },
        "rows": rows,
    }


_REPORT_HANDLERS = {
    "sales": _sales_report,
    "inventory": _inventory_report,
    "top_products": _top_products_report,
    "top_sellers": _top_products_report,
    "customers": _customers_report,
    "invoices": _invoices_report,
    "categories": _categories_report,
    "purchases": _purchases_report,
    "gst": _gst_report,
    "gst_summary": _gst_report,
    "revenue_summary": _sales_report,
    "overview": _overview_report,
    "stock_check": _inventory_report,
}


async def generate_store_report(
    db: AsyncSession,
    store_id: int,
    message: str = "",
    params: dict | None = None,
    customer_id: int | None = None,
) -> dict[str, Any]:
    """Run a report query and return structured data for the chat UI."""
    rp = parse_report_params(message, params)
    if customer_id and not rp.customer_id:
        rp.customer_id = customer_id

    handler = _REPORT_HANDLERS.get(rp.report_type, _overview_report)
    return await handler(db, store_id, rp)


def report_to_agent_data(report: dict[str, Any]) -> dict[str, Any]:
    """Shape report payload for AgentResponse.data (table-friendly)."""
    return {
        "report_type": report.get("report_type"),
        "title": report.get("title"),
        "summary": report.get("summary"),
        "metrics": report.get("metrics"),
        "items": report.get("rows") or [],
    }
