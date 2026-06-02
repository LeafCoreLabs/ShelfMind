from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.store import Store, Transaction
from app.models.user import User
from app.schemas.admin import StoreCreate, StoreUpdate
from app.services.audit import log_audit

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/stores")
async def list_stores(db: AsyncSession = Depends(get_db)):
    stores = (await db.execute(select(Store).order_by(Store.created_at.desc()))).scalars().all()
    result = []
    for store in stores:
        owner_count = (
            await db.execute(
                select(func.count(User.id)).where(User.store_id == store.id, User.is_active == True)
            )
        ).scalar() or 0
        tx_count = (
            await db.execute(select(func.count(Transaction.id)).where(Transaction.store_id == store.id))
        ).scalar() or 0
        revenue = (
            await db.execute(
                select(func.sum(Transaction.quantity * Transaction.unit_price)).where(
                    Transaction.store_id == store.id
                )
            )
        ).scalar() or 0
        result.append(
            {
                "id": store.id,
                "name": store.name,
                "location": store.location,
                "lat": store.lat,
                "lon": store.lon,
                "phone": store.phone,
                "business_type": store.business_type,
                "is_active": store.is_active,
                "owner_count": owner_count,
                "transaction_count": tx_count,
                "revenue": round(float(revenue), 2),
            }
        )
    return {"stores": result}


@router.post("/stores")
async def create_store(
    body: StoreCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    store = Store(
        name=body.name,
        location=body.location,
        lat=body.lat,
        lon=body.lon,
        salary_cycle_day=body.salary_cycle_day,
        phone=body.phone,
        business_type=body.business_type,
        timezone=body.timezone,
        preferences=body.preferences,
    )
    db.add(store)
    await db.commit()
    await db.refresh(store)
    await log_audit(db, actor.email, "create", "store", {"store_id": store.id, "name": store.name})
    return {"id": store.id, "name": store.name}


@router.get("/stores/{store_id}")
async def get_store(store_id: int, db: AsyncSession = Depends(get_db)):
    store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    users = (
        await db.execute(select(User).where(User.store_id == store_id))
    ).scalars().all()
    return {
        "store": {
            "id": store.id,
            "name": store.name,
            "location": store.location,
            "lat": store.lat,
            "lon": store.lon,
            "salary_cycle_day": store.salary_cycle_day,
            "phone": store.phone,
            "business_type": store.business_type,
            "timezone": store.timezone,
            "preferences": store.preferences,
            "is_active": store.is_active,
        },
        "users": [{"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role} for u in users],
    }


@router.patch("/stores/{store_id}")
async def update_store(
    store_id: int,
    body: StoreUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    for field in ("name", "location", "lat", "lon", "salary_cycle_day", "phone", "business_type", "timezone", "preferences", "is_active"):
        val = getattr(body, field)
        if val is not None:
            setattr(store, field, val)
    await db.commit()
    await log_audit(db, actor.email, "update", "store", {"store_id": store_id})
    return {"updated": True, "store_id": store_id}


@router.delete("/stores/{store_id}")
async def deactivate_store(
    store_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    store.is_active = False
    await db.commit()
    await log_audit(db, actor.email, "deactivate", "store", {"store_id": store_id})
    return {"deactivated": True, "store_id": store_id}
