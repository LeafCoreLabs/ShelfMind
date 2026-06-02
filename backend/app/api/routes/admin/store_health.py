from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.session import get_db
from app.services.store_health import compute_store_health

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/store-health")
async def store_health(db: AsyncSession = Depends(get_db)):
    scorecards = await compute_store_health(db)
    avg = round(sum(s["health_score"] for s in scorecards) / len(scorecards)) if scorecards else 0
    return {"average_score": avg, "stores": scorecards}
