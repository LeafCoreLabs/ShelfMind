from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_owner_store_id, require_store_owner
from app.db.session import get_db
from app.models.commerce import Customer
from app.services.commerce_ops import create_customer_record

router = APIRouter(dependencies=[Depends(require_store_owner)])


class CustomerCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    segment: str = "Regular"
    notes: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    segment: str | None = None
    notes: str | None = None


@router.get("/customers")
async def list_customers(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    rows = (await db.execute(select(Customer).where(Customer.store_id == store_id).order_by(Customer.name))).scalars().all()
    return {
        "customers": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "segment": c.segment,
                "total_spent": c.total_spent,
                "last_purchase_at": c.last_purchase_at.isoformat() if c.last_purchase_at else None,
            }
            for c in rows
        ]
    }


@router.post("/customers")
async def create_customer(
    body: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    c = await create_customer_record(
        db, store_id, body.name, body.email, body.phone, body.segment, body.notes
    )
    await db.commit()
    return {"id": c.id, "name": c.name}


@router.patch("/customers/{customer_id}")
async def update_customer(
    customer_id: int,
    body: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    c = (
        await db.execute(select(Customer).where(Customer.id == customer_id, Customer.store_id == store_id))
    ).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(c, field, val)
    await db.commit()
    return {"updated": True}


@router.delete("/customers/{customer_id}")
async def delete_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    c = (
        await db.execute(select(Customer).where(Customer.id == customer_id, Customer.store_id == store_id))
    ).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    await db.delete(c)
    await db.commit()
    return {"deleted": True}
