from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_owner_store_id, require_store_owner
from app.db.session import get_db
from app.models.commerce import Invoice
from app.models.store import Product, Store, Transaction
from app.services.commerce_ops import (
    SaleLine,
    apply_batch_sale,
    apply_sale,
    create_invoice_from_transactions,
    invoice_payload,
    record_invoice_payment,
    store_gst_context,
    update_customer_spend,
)

router = APIRouter(dependencies=[Depends(require_store_owner)])


class PaymentCreate(BaseModel):
    amount: float
    method: str = "cash"
    reference: str | None = None


class SaleCreate(BaseModel):
    product_id: int
    quantity: int
    unit_price: float | None = None
    customer_id: int | None = None


class SaleLineCreate(BaseModel):
    product_id: int
    quantity: int
    unit_price: float | None = None


class BatchSaleCreate(BaseModel):
    lines: list[SaleLineCreate]
    customer_id: int | None = None


class InvoiceFromSalesCreate(BaseModel):
    transaction_ids: list[int]


@router.get("/sales")
async def list_sales(
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
    limit: int = 100,
):
    rows = (
        await db.execute(
            select(Transaction, Product)
            .join(Product, Product.id == Transaction.product_id)
            .where(Transaction.store_id == store_id)
            .order_by(Transaction.sold_at.desc())
            .limit(limit)
        )
    ).all()
    return {
        "sales": [
            {
                "id": t.id,
                "sku": p.sku,
                "product_name": p.name,
                "quantity": t.quantity,
                "unit_price": t.unit_price,
                "total": round(t.quantity * t.unit_price, 2),
                "customer_id": t.customer_id,
                "sold_at": t.sold_at.isoformat(),
            }
            for t, p in rows
        ]
    }


@router.post("/sales")
async def create_sale(
    body: SaleCreate,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    txn = await apply_sale(db, store_id, body.product_id, body.quantity, body.unit_price, body.customer_id)
    total = round(body.quantity * (body.unit_price or 0), 2)
    product = (await db.execute(select(Product).where(Product.id == body.product_id))).scalar_one()
    if body.unit_price is None:
        total = round(body.quantity * product.list_price, 2)
    await update_customer_spend(db, store_id, body.customer_id, total)
    await db.commit()
    await db.refresh(txn)
    return {"id": txn.id, "total": total}


@router.post("/sales/batch")
async def create_batch_sale(
    body: BatchSaleCreate,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    lines = [
        SaleLine(product_id=ln.product_id, quantity=ln.quantity, unit_price=ln.unit_price)
        for ln in body.lines
    ]
    txn_ids, total = await apply_batch_sale(db, store_id, lines, body.customer_id)
    await db.commit()
    return {"transaction_ids": txn_ids, "total": total}


@router.get("/billing/invoices")
async def list_invoices(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    gstin, _ = await store_gst_context(db, store_id)
    rows = (await db.execute(select(Invoice).where(Invoice.store_id == store_id).order_by(Invoice.issued_at.desc()))).scalars().all()
    return {"invoices": [invoice_payload(inv, gstin) for inv in rows], "store_gstin": gstin}


@router.get("/billing/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    gstin, _ = await store_gst_context(db, store_id)
    store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one()
    inv = (
        await db.execute(
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.store_id == store_id)
            .options(selectinload(Invoice.lines), selectinload(Invoice.customer))
        )
    ).scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {
        **invoice_payload(inv, gstin),
        "store_name": store.name,
        "store_location": store.location,
        "customer_name": inv.customer.name if inv.customer else "Walk-in",
        "lines": [
            {
                "description": ln.description,
                "hsn_code": ln.hsn_code,
                "quantity": ln.quantity,
                "unit_price": ln.unit_price,
                "line_total": ln.line_total,
            }
            for ln in inv.lines
        ],
    }


@router.post("/billing/invoices/from-sale/{transaction_id}")
async def invoice_from_sale(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    inv = await create_invoice_from_transactions(db, store_id, [transaction_id])
    await db.commit()
    return {"invoice_id": inv.id, "invoice_number": inv.invoice_number, "total": inv.total}


@router.post("/billing/invoices/from-sales")
async def invoice_from_sales(
    body: InvoiceFromSalesCreate,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    inv = await create_invoice_from_transactions(db, store_id, body.transaction_ids)
    await db.commit()
    return {"invoice_id": inv.id, "invoice_number": inv.invoice_number, "total": inv.total}


@router.post("/billing/invoices/{invoice_id}/pay")
async def record_payment(
    invoice_id: int,
    body: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    return await record_invoice_payment(db, store_id, invoice_id, body.amount, body.method, body.reference)
