from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_owner_store_id, require_store_owner
from app.db.session import get_db
from app.models.store import Store

router = APIRouter(dependencies=[Depends(require_store_owner)])


class StoreSettingsUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    phone: str | None = None
    business_type: str | None = None
    timezone: str | None = None
    preferences: dict | None = None
    gstin: str | None = None
    place_of_supply: str | None = None


@router.get("/settings")
async def get_settings(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one()
    prefs = store.preferences or {}
    return {
        "id": store.id,
        "name": store.name,
        "location": store.location,
        "phone": store.phone,
        "business_type": store.business_type,
        "timezone": store.timezone,
        "preferences": prefs,
        "gstin": prefs.get("gstin"),
        "place_of_supply": prefs.get("place_of_supply"),
    }


@router.patch("/settings")
async def update_settings(
    body: StoreSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one()
    data = body.model_dump(exclude_unset=True)
    gstin = data.pop("gstin", None)
    place = data.pop("place_of_supply", None)
    if gstin is not None or place is not None:
        prefs = dict(store.preferences or {})
        if gstin is not None:
            prefs["gstin"] = gstin
        if place is not None:
            prefs["place_of_supply"] = place
        store.preferences = prefs
    for field, val in data.items():
        setattr(store, field, val)
    await db.commit()
    return {"updated": True}
