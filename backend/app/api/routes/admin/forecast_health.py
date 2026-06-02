from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.session import get_db
from app.services.forecast_accuracy import compute_forecast_accuracy

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/forecast-accuracy")
async def forecast_accuracy(
    db: AsyncSession = Depends(get_db),
    store_id: int | None = Query(None),
    days: int = Query(14, le=30),
):
    return await compute_forecast_accuracy(db, store_id=store_id, days=days)
