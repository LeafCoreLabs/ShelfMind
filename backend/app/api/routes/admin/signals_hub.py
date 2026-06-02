from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.store import ExternalSignal, Store

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/signals/map")
async def signals_map(db: AsyncSession = Depends(get_db)):
    stores = (await db.execute(select(Store).where(Store.is_active == True))).scalars().all()
    signals = (await db.execute(select(ExternalSignal).order_by(ExternalSignal.created_at.desc()))).scalars().all()

    store_pins = [
        {
            "id": s.id,
            "name": s.name,
            "location": s.location,
            "lat": s.lat,
            "lon": s.lon,
            "signal_count": len(signals),
        }
        for s in stores
    ]

    feed = [
        {
            "id": sig.id,
            "signal_type": sig.signal_type,
            "category": sig.category,
            "value": sig.value,
            "description": sig.description,
            "impact_score": round(abs(sig.value) * 10, 1),
            "effective_from": sig.effective_from.isoformat(),
            "effective_to": sig.effective_to.isoformat(),
        }
        for sig in signals
    ]

    return {"stores": store_pins, "signals": feed}


@router.get("/signals")
async def list_signals_filtered(
    db: AsyncSession = Depends(get_db),
    signal_type: str | None = Query(None),
    store_id: int | None = Query(None),
):
    q = select(ExternalSignal).order_by(ExternalSignal.created_at.desc())
    if signal_type:
        q = q.where(ExternalSignal.signal_type == signal_type)
    rows = (await db.execute(q)).scalars().all()
    stores = (await db.execute(select(Store).where(Store.is_active == True))).scalars().all()
    if store_id:
        stores = [s for s in stores if s.id == store_id]

    return {
        "stores": [{"id": s.id, "name": s.name, "lat": s.lat, "lon": s.lon} for s in stores],
        "signals": [
            {
                "id": s.id,
                "signal_type": s.signal_type,
                "category": s.category,
                "value": s.value,
                "description": s.description,
                "impact_score": round(abs(s.value) * 10, 1),
            }
            for s in rows
        ],
    }
