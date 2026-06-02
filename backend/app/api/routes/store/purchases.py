from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_owner_store_id, require_store_owner
from app.db.session import get_db
from app.services.commerce_ops import create_purchase_order, create_vendor_record, receive_purchase_order
from app.models.commerce import PurchaseOrder, Vendor

router = APIRouter(dependencies=[Depends(require_store_owner)])


class VendorCreate(BaseModel):
    name: str
    phone: str | None = None
    gstin: str | None = None
    email: str | None = None


class PurchaseLineCreate(BaseModel):
    product_id: int
    qty: int
    unit_cost: float | None = None


class PurchaseCreate(BaseModel):
    vendor_id: int
    lines: list[PurchaseLineCreate]


@router.get("/vendors")
async def list_vendors(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    rows = (await db.execute(select(Vendor).where(Vendor.store_id == store_id).order_by(Vendor.name))).scalars().all()
    return {
        "vendors": [
            {"id": v.id, "name": v.name, "phone": v.phone, "gstin": v.gstin, "email": v.email}
            for v in rows
        ]
    }


@router.post("/vendors")
async def create_vendor(
    body: VendorCreate,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    vendor = await create_vendor_record(
        db, store_id, body.name, body.phone, body.gstin, body.email
    )
    await db.commit()
    return {"id": vendor.id, "name": vendor.name}


@router.get("/purchases")
async def list_purchases(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    rows = (
        await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.store_id == store_id)
            .options(selectinload(PurchaseOrder.vendor), selectinload(PurchaseOrder.lines))
            .order_by(PurchaseOrder.ordered_at.desc())
        )
    ).scalars().all()
    return {
        "purchases": [
            {
                "id": po.id,
                "vendor_id": po.vendor_id,
                "vendor_name": po.vendor.name if po.vendor else "",
                "status": po.status,
                "subtotal": po.subtotal,
                "tax": po.tax,
                "total": po.total,
                "ordered_at": po.ordered_at.isoformat(),
                "received_at": po.received_at.isoformat() if po.received_at else None,
                "lines": [
                    {
                        "product_id": ln.product_id,
                        "qty": ln.qty,
                        "unit_cost": ln.unit_cost,
                        "line_total": ln.line_total,
                    }
                    for ln in po.lines
                ],
            }
            for po in rows
        ]
    }


@router.post("/purchases")
async def create_purchase(
    body: PurchaseCreate,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    lines = [
        {"product_id": ln.product_id, "qty": ln.qty, "unit_cost": ln.unit_cost}
        for ln in body.lines
    ]
    result = await create_purchase_order(db, store_id, body.vendor_id, lines)
    await db.commit()
    return result


@router.post("/purchases/{po_id}/receive")
async def receive_purchase(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    result = await receive_purchase_order(db, store_id, po_id)
    await db.commit()
    return result
