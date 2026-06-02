from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.admin import AlertEvent, AlertRule
from app.models.user import User
from app.services.audit import log_audit

router = APIRouter(dependencies=[Depends(require_admin)])


class AlertRuleCreate(BaseModel):
    name: str
    rule_type: str
    threshold: float


@router.get("/alert-rules")
async def list_alert_rules(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(AlertRule).order_by(AlertRule.created_at.desc()))).scalars().all()
    return {
        "rules": [
            {"id": r.id, "name": r.name, "rule_type": r.rule_type, "threshold": r.threshold, "is_active": r.is_active}
            for r in rows
        ]
    }


@router.post("/alert-rules")
async def create_alert_rule(
    body: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rule = AlertRule(name=body.name, rule_type=body.rule_type, threshold=body.threshold)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    await log_audit(db, user.email, "create", "alert_rule", {"rule_id": rule.id, "name": rule.name})
    return {"id": rule.id, "name": rule.name}


@router.get("/alerts")
async def list_alerts(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(AlertEvent).order_by(AlertEvent.created_at.desc()).limit(50))).scalars().all()
    return {
        "alerts": [
            {
                "id": a.id,
                "rule_id": a.rule_id,
                "severity": a.severity,
                "title": a.title,
                "message": a.message,
                "store_id": a.store_id,
                "acknowledged": a.acknowledged,
                "created_at": a.created_at.isoformat(),
            }
            for a in rows
        ]
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(AlertEvent).where(AlertEvent.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.execute(update(AlertEvent).where(AlertEvent.id == alert_id).values(acknowledged=True))
    await db.commit()
    await log_audit(db, user.email, "acknowledge", "alert", {"alert_id": alert_id})
    return {"acknowledged": True}
