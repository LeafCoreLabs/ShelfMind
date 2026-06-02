from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.services.audit import log_audit
from app.services.restock_planner import generate_restock_plan, publish_restock_plan

router = APIRouter(dependencies=[Depends(require_admin)])


class RestockPlanRequest(BaseModel):
    store_ids: list[int] | None = None
    categories: list[str] | None = None


class RestockPublishRequest(BaseModel):
    plan: list[dict]


@router.post("/restock/plan")
async def create_restock_plan(body: RestockPlanRequest, db: AsyncSession = Depends(get_db)):
    plan = await generate_restock_plan(db, store_ids=body.store_ids, categories=body.categories)
    return {"plan": plan, "count": len(plan)}


@router.post("/restock/publish")
async def publish_plan(
    body: RestockPublishRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    count = await publish_restock_plan(db, body.plan)
    await log_audit(db, user.email, "publish", "restock_plan", {"items": count})
    return {"published": count}
