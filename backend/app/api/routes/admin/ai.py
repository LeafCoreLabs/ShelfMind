from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import require_admin
from app.db.session import get_db
from app.services.admin_nl_query import explain_insight

router = APIRouter(dependencies=[Depends(require_admin)])


class ExplainRequest(BaseModel):
    title: str
    detail: str
    insight_type: str = "anomaly"


@router.get("/ai/status")
async def ai_status():
    settings = get_settings()
    return {
        "enabled": bool(settings.llm_api_key),
        "provider": settings.llm_provider,
        "model": settings.llm_model or "demo-fallback",
    }


@router.post("/insights/explain")
async def explain_insight_endpoint(body: ExplainRequest, db: AsyncSession = Depends(get_db)):
    result = await explain_insight(db, body.title, body.detail, body.insight_type)
    return result
