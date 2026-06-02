from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.session import get_db
from app.services.anomaly_detector import detect_anomalies

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/anomalies")
async def list_anomalies(db: AsyncSession = Depends(get_db)):
    anomalies = await detect_anomalies(db)
    return {"anomalies": anomalies, "count": len(anomalies)}
