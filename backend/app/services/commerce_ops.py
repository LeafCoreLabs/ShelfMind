"""Shared store write operations for API routes and chat agent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.commerce import (
    Customer,
    Invoice,
    InvoiceLine,
    Payment,
    PurchaseLine,
    PurchaseOrder,
    Vendor,
    hsn_for_category,
    split_gst,
)
from app.models.store import Product, Store, Transaction


@dataclass
class SaleLine:
    product_id: int
    quantity: int
    unit_price: float | None = None


def fuzzy_match_entity(name: str, candidates: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Return matching (id, label) pairs sorted by relevance."""
    if not name or not candidates:
        return []
    q = name.lower().strip()
    exact = [(i, lbl) for i, lbl in candidates if lbl.lower() == q]
    if exact:
        return exact
    starts = [(i, lbl) for i, lbl in candidates if lbl.lower().startswith(q)]
    if starts:
        return starts
    contains = [(i, lbl) for i, lbl in candidates if q in lbl.lower()]
    return contains


async def apply_sale(
    db: AsyncSession,
    store_id: int,
    product_id: int,
    quantity: int,
    unit_price: float | None,
    customer_id: int | None,
) -> Transaction:
    product = (
        await db.execute(select(Product).where(Product.id == product_id, Product.store_id == store_id))
    ).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock_on_hand < quantity:
        raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name}")
    price = unit_price if unit_price is not None else product.list_price
    txn = Transaction(
        store_id=store_id,
        product_id=product.id,
        quantity=quantity,
        unit_price=price,
        sold_at=datetime.now(timezone.utc),
        customer_id=customer_id,
    )
    product.stock_on_hand -= quantity
    db.add(txn)
    return txn


async def apply_batch_sale(
    db: AsyncSession,
    store_id: int,
    lines: list[SaleLine],
    customer_id: int | None,
) -> tuple[list[int], float]:
    if not lines:
        raise HTTPException(status_code=400, detail="At least one line required")
    txn_ids: list[int] = []
    total = 0.0
    for line in lines:
        txn = await apply_sale(db, store_id, line.product_id, line.quantity, line.unit_price, customer_id)
        await db.flush()
        line_total = round(line.quantity * txn.unit_price, 2)
        total += line_total
        txn_ids.append(txn.id)
    await update_customer_spend(db, store_id, customer_id, total)
    return txn_ids, round(total, 2)


async def update_customer_spend(
    db: AsyncSession, store_id: int, customer_id: int | None, amount: float
) -> None:
    if not customer_id:
        return
    customer = (
        await db.execute(select(Customer).where(Customer.id == customer_id, Customer.store_id == store_id))
    ).scalar_one_or_none()
    if customer:
        customer.total_spent += amount
        customer.last_purchase_at = datetime.now(timezone.utc)


async def store_gst_context(db: AsyncSession, store_id: int) -> tuple[str | None, str]:
    store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one()
    prefs = store.preferences or {}
    gstin = prefs.get("gstin")
    place = prefs.get("place_of_supply") or (store.location.split(",")[0].strip() if store.location else "India")
    return gstin, place


def invoice_payload(inv: Invoice, gstin: str | None = None) -> dict:
    cgst = inv.cgst_amount
    sgst = inv.sgst_amount
    igst = inv.igst_amount
    if inv.tax_amount > 0 and cgst == 0 and sgst == 0 and igst == 0:
        _, cgst, sgst, igst = split_gst(inv.subtotal)
    return {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "status": inv.status,
        "customer_id": inv.customer_id,
        "subtotal": inv.subtotal,
        "tax_amount": inv.tax_amount,
        "cgst_amount": cgst,
        "sgst_amount": sgst,
        "igst_amount": igst,
        "place_of_supply": inv.place_of_supply,
        "total": inv.total,
        "issued_at": inv.issued_at.isoformat(),
        "gstin": gstin,
    }


async def create_invoice_from_transactions(
    db: AsyncSession,
    store_id: int,
    transaction_ids: list[int],
    customer_id: int | None = None,
) -> Invoice:
    if not transaction_ids:
        raise HTTPException(status_code=400, detail="No transactions provided")

    rows = (
        await db.execute(
            select(Transaction, Product)
            .join(Product, Product.id == Transaction.product_id)
            .where(Transaction.id.in_(transaction_ids), Transaction.store_id == store_id)
        )
    ).all()
    if len(rows) != len(transaction_ids):
        raise HTTPException(status_code=404, detail="One or more sales not found")

    _, place = await store_gst_context(db, store_id)
    subtotal = sum(t.quantity * t.unit_price for t, _ in rows)
    subtotal = round(subtotal, 2)
    tax, cgst, sgst, igst = split_gst(subtotal, intra_state=True)
    total = round(subtotal + tax, 2)
    resolved_customer = customer_id or next((t.customer_id for t, _ in rows if t.customer_id), None)

    count = (await db.execute(select(Invoice).where(Invoice.store_id == store_id))).scalars().all()
    inv_num = f"INV-{store_id}-{len(count) + 1:04d}"
    inv = Invoice(
        store_id=store_id,
        customer_id=resolved_customer,
        invoice_number=inv_num,
        status="sent",
        subtotal=subtotal,
        tax_amount=tax,
        cgst_amount=cgst,
        sgst_amount=sgst,
        igst_amount=igst,
        place_of_supply=place,
        total=total,
        due_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(inv)
    await db.flush()
    for t, p in rows:
        line_total = round(t.quantity * t.unit_price, 2)
        db.add(
            InvoiceLine(
                invoice_id=inv.id,
                product_id=p.id,
                description=p.name,
                hsn_code=hsn_for_category(p.category),
                quantity=t.quantity,
                unit_price=t.unit_price,
                line_total=line_total,
            )
        )
    return inv


async def create_invoice_for_customer(
    db: AsyncSession,
    store_id: int,
    customer_id: int | None,
    lines: list[SaleLine],
) -> dict:
    txn_ids, sale_total = await apply_batch_sale(db, store_id, lines, customer_id)
    inv = await create_invoice_from_transactions(db, store_id, txn_ids, customer_id)
    await db.commit()
    return {
        "invoice_id": inv.id,
        "invoice_number": inv.invoice_number,
        "total": inv.total,
        "sale_total": sale_total,
        "transaction_ids": txn_ids,
    }


async def record_invoice_payment(
    db: AsyncSession,
    store_id: int,
    invoice_id: int,
    amount: float,
    method: str = "cash",
    reference: str | None = None,
) -> dict:
    inv = (
        await db.execute(select(Invoice).where(Invoice.id == invoice_id, Invoice.store_id == store_id))
    ).scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    db.add(Payment(invoice_id=inv.id, amount=amount, method=method, reference=reference))
    existing = (await db.execute(select(Payment).where(Payment.invoice_id == inv.id))).scalars().all()
    total_paid = sum(p.amount for p in existing) + amount
    if total_paid >= inv.total:
        inv.status = "paid"
    await db.commit()
    return {"status": inv.status, "paid_amount": total_paid, "invoice_number": inv.invoice_number}


async def adjust_product_stock(
    db: AsyncSession,
    store_id: int,
    product_id: int,
    delta: int,
) -> dict:
    product = (
        await db.execute(select(Product).where(Product.id == product_id, Product.store_id == store_id))
    ).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.stock_on_hand = max(0, product.stock_on_hand + delta)
    await db.commit()
    return {"product_id": product.id, "product_name": product.name, "stock_on_hand": product.stock_on_hand}


async def create_customer_record(
    db: AsyncSession,
    store_id: int,
    name: str,
    email: str | None = None,
    phone: str | None = None,
    segment: str = "Regular",
) -> dict:
    c = Customer(store_id=store_id, name=name, email=email, phone=phone, segment=segment)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return {"id": c.id, "name": c.name, "segment": c.segment}


async def create_vendor_record(
    db: AsyncSession,
    store_id: int,
    name: str,
    phone: str | None = None,
    gstin: str | None = None,
    email: str | None = None,
) -> dict:
    vendor = Vendor(store_id=store_id, name=name, phone=phone, gstin=gstin, email=email)
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)
    return {"id": vendor.id, "name": vendor.name}


async def create_purchase_order(
    db: AsyncSession,
    store_id: int,
    vendor_id: int,
    lines: list[tuple[int, int, float | None]],
) -> dict:
    vendor = (
        await db.execute(select(Vendor).where(Vendor.id == vendor_id, Vendor.store_id == store_id))
    ).scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if not lines:
        raise HTTPException(status_code=400, detail="At least one line required")

    subtotal = 0.0
    line_data: list[tuple[Product, int, float, float]] = []
    for product_id, qty, unit_cost in lines:
        product = (
            await db.execute(select(Product).where(Product.id == product_id, Product.store_id == store_id))
        ).scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
        cost = unit_cost if unit_cost is not None else product.cost_price
        line_total = round(qty * cost, 2)
        subtotal += line_total
        line_data.append((product, qty, cost, line_total))

    tax = round(subtotal * 0.18, 2)
    total = round(subtotal + tax, 2)
    po = PurchaseOrder(
        store_id=store_id,
        vendor_id=vendor.id,
        status="ordered",
        subtotal=subtotal,
        tax=tax,
        total=total,
    )
    db.add(po)
    await db.flush()
    for product, qty, cost, line_total in line_data:
        db.add(
            PurchaseLine(
                po_id=po.id,
                product_id=product.id,
                qty=qty,
                unit_cost=cost,
                line_total=line_total,
            )
        )
    await db.commit()
    return {"id": po.id, "total": total, "status": po.status, "vendor_name": vendor.name}


async def receive_purchase_order(db: AsyncSession, store_id: int, po_id: int) -> dict:
    po = (
        await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id, PurchaseOrder.store_id == store_id)
            .options(selectinload(PurchaseOrder.lines))
        )
    ).scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status == "received":
        raise HTTPException(status_code=400, detail="Already received")

    for line in po.lines:
        product = (
            await db.execute(select(Product).where(Product.id == line.product_id, Product.store_id == store_id))
        ).scalar_one_or_none()
        if product:
            product.stock_on_hand += line.qty

    po.status = "received"
    po.received_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": po.id, "status": po.status}
