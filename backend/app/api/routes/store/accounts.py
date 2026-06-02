from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_owner_store_id, require_store_owner
from app.db.session import get_db
from app.models.commerce import Invoice, Payment, PurchaseOrder
from app.models.store import Product, Transaction

router = APIRouter(dependencies=[Depends(require_store_owner)])


def _parse_range(from_date: str | None, to_date: str | None) -> tuple[datetime, datetime]:
    today = date.today()
    start = date.fromisoformat(from_date) if from_date else today.replace(day=1)
    end = date.fromisoformat(to_date) if to_date else today
    start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end, time.max, tzinfo=timezone.utc)
    return start_dt, end_dt


@router.get("/reports/pnl")
async def profit_and_loss(
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
):
    start_dt, end_dt = _parse_range(from_date, to_date)

    revenue = (
        await db.execute(
            select(func.coalesce(func.sum(Transaction.quantity * Transaction.unit_price), 0)).where(
                Transaction.store_id == store_id,
                Transaction.sold_at >= start_dt,
                Transaction.sold_at <= end_dt,
            )
        )
    ).scalar() or 0

    cogs = (
        await db.execute(
            select(func.coalesce(func.sum(PurchaseOrder.subtotal), 0)).where(
                PurchaseOrder.store_id == store_id,
                PurchaseOrder.status == "received",
                PurchaseOrder.received_at >= start_dt,
                PurchaseOrder.received_at <= end_dt,
            )
        )
    ).scalar() or 0

    tax_collected = (
        await db.execute(
            select(func.coalesce(func.sum(Invoice.tax_amount), 0)).where(
                Invoice.store_id == store_id,
                Invoice.issued_at >= start_dt,
                Invoice.issued_at <= end_dt,
            )
        )
    ).scalar() or 0

    revenue = round(float(revenue), 2)
    cogs = round(float(cogs), 2)
    tax_collected = round(float(tax_collected), 2)
    gross_margin = round(revenue - cogs, 2)
    margin_pct = round((gross_margin / revenue * 100) if revenue else 0, 1)

    return {
        "from": start_dt.date().isoformat(),
        "to": end_dt.date().isoformat(),
        "revenue": revenue,
        "cogs": cogs,
        "gross_margin": gross_margin,
        "margin_pct": margin_pct,
        "tax_collected": tax_collected,
    }


@router.get("/reports/daybook")
async def day_book(
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
    date_str: str | None = Query(None, alias="date"),
):
    day = date.fromisoformat(date_str) if date_str else date.today()
    start_dt = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(day, time.max, tzinfo=timezone.utc)

    entries: list[dict] = []

    sales = (
        await db.execute(
            select(Transaction, Product)
            .join(Product, Product.id == Transaction.product_id)
            .where(
                Transaction.store_id == store_id,
                Transaction.sold_at >= start_dt,
                Transaction.sold_at <= end_dt,
            )
            .order_by(Transaction.sold_at)
        )
    ).all()
    for txn, product in sales:
        total = round(txn.quantity * txn.unit_price, 2)
        entries.append(
            {
                "time": txn.sold_at.isoformat(),
                "type": "sale",
                "description": f"Sale — {product.name} × {txn.quantity}",
                "debit": 0,
                "credit": total,
            }
        )

    payments = (
        await db.execute(
            select(Payment, Invoice)
            .join(Invoice, Invoice.id == Payment.invoice_id)
            .where(
                Invoice.store_id == store_id,
                Payment.paid_at >= start_dt,
                Payment.paid_at <= end_dt,
            )
            .order_by(Payment.paid_at)
        )
    ).all()
    for pay, inv in payments:
        entries.append(
            {
                "time": pay.paid_at.isoformat(),
                "type": "payment",
                "description": f"Payment — {inv.invoice_number} ({pay.method})",
                "debit": pay.amount,
                "credit": 0,
            }
        )

    purchases = (
        await db.execute(
            select(PurchaseOrder)
            .where(
                PurchaseOrder.store_id == store_id,
                PurchaseOrder.ordered_at >= start_dt,
                PurchaseOrder.ordered_at <= end_dt,
            )
            .options(selectinload(PurchaseOrder.vendor))
            .order_by(PurchaseOrder.ordered_at)
        )
    ).scalars().all()
    for po in purchases:
        vendor_name = po.vendor.name if po.vendor else "Vendor"
        entries.append(
            {
                "time": (po.received_at or po.ordered_at).isoformat(),
                "type": "purchase",
                "description": f"Purchase — {vendor_name} ({po.status})",
                "debit": po.total,
                "credit": 0,
            }
        )

    entries.sort(key=lambda e: e["time"])
    return {"date": day.isoformat(), "entries": entries}
