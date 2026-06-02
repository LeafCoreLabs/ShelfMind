from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.admin import AuditLog
from app.models.store import Recommendation
from app.models.user import User

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/audit")
async def audit_timeline(db: AsyncSession = Depends(get_db), limit: int = Query(50, le=200)):
    logs = (await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))).scalars().all()
    recs = (await db.execute(select(Recommendation).order_by(Recommendation.created_at.desc()).limit(20))).scalars().all()
    users = (await db.execute(select(User).order_by(User.created_at.desc()).limit(10))).scalars().all()

    events = [
        {
            "type": "audit",
            "actor": l.actor_email,
            "action": l.action,
            "resource": l.resource,
            "detail": l.detail,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
    for r in recs:
        events.append(
            {
                "type": "recommendation",
                "actor": "system",
                "action": r.action,
                "resource": r.product_name,
                "detail": {"query": r.query, "store_id": r.store_id, "delta_pct": r.delta_pct},
                "created_at": r.created_at.isoformat(),
            }
        )
    for u in users:
        events.append(
            {
                "type": "user",
                "actor": "system",
                "action": "user_created",
                "resource": u.email,
                "detail": {"role": u.role},
                "created_at": u.created_at.isoformat(),
            }
        )

    events.sort(key=lambda x: x["created_at"], reverse=True)
    return {"events": events[:limit]}


@router.get("/reports")
async def list_reports():
    from datetime import datetime, timezone

    from app.config import get_settings

    settings = get_settings()
    key = f"reports/weekly-{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return {
        "reports": [
            {
                "name": "Weekly Forecast Export",
                "key": key,
                "schedule": "Every Monday 4:00 AM IST",
                "status": "scheduled",
            },
            {
                "name": "Multi-store Platform Bundle",
                "key": "reports/platform-bundle.csv",
                "schedule": "On demand via job trigger",
                "status": "available",
            },
        ],
        "bucket": settings.s3_bucket,
    }
