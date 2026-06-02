from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.store import (
    ExternalSignal,
    Forecast,
    PeerBenchmark,
    Product,
    Recommendation,
    Store,
    Transaction,
)
from app.models.user import OnboardingDraft, User

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/stats")
async def platform_stats(db: AsyncSession = Depends(get_db)):
    stores = (await db.execute(select(func.count(Store.id)).where(Store.is_active == True))).scalar() or 0
    users = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar() or 0
    transactions = (await db.execute(select(func.count(Transaction.id)))).scalar() or 0
    forecasts = (await db.execute(select(func.count(Forecast.id)))).scalar() or 0
    signals = (await db.execute(select(func.count(ExternalSignal.id)))).scalar() or 0
    revenue = (
        await db.execute(select(func.sum(Transaction.quantity * Transaction.unit_price)))
    ).scalar() or 0
    drafts = (
        await db.execute(
            select(func.count(OnboardingDraft.id)).where(OnboardingDraft.status == "draft")
        )
    ).scalar() or 0

    return {
        "total_stores": stores,
        "active_users": users,
        "total_transactions": transactions,
        "forecasts_generated": forecasts,
        "signals_live": signals,
        "platform_revenue": round(float(revenue), 2),
        "onboarding_drafts_pending": drafts,
    }


@router.get("/activity")
async def recent_activity(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, le=100),
):
    recs = (
        await db.execute(
            select(Recommendation).order_by(Recommendation.created_at.desc()).limit(limit)
        )
    ).scalars().all()

    users = (
        await db.execute(select(User).order_by(User.created_at.desc()).limit(limit))
    ).scalars().all()

    return {
        "recent_recommendations": [
            {
                "id": r.id,
                "store_id": r.store_id,
                "query": r.query,
                "sku": r.sku,
                "product_name": r.product_name,
                "action": r.action,
                "created_at": r.created_at.isoformat(),
            }
            for r in recs
        ],
        "recent_users": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
    }


@router.get("/signals")
async def list_signals(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(ExternalSignal).order_by(ExternalSignal.created_at.desc()))).scalars().all()
    return {
        "signals": [
            {
                "id": s.id,
                "signal_type": s.signal_type,
                "category": s.category,
                "value": s.value,
                "description": s.description,
                "effective_from": s.effective_from.isoformat(),
                "effective_to": s.effective_to.isoformat(),
            }
            for s in rows
        ]
    }


@router.get("/peer-benchmarks")
async def list_peer_benchmarks(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(PeerBenchmark).order_by(PeerBenchmark.category))).scalars().all()
    return {
        "benchmarks": [
            {
                "id": b.id,
                "category": b.category,
                "sku": b.sku,
                "peer_avg_daily": b.peer_avg_daily,
                "local_avg_daily": b.local_avg_daily,
                "lift_pct": b.lift_pct,
            }
            for b in rows
        ]
    }


@router.get("/recommendations")
async def list_recommendations(
    db: AsyncSession = Depends(get_db),
    store_id: int | None = Query(None),
    limit: int = Query(50, le=200),
):
    q = select(Recommendation).order_by(Recommendation.created_at.desc()).limit(limit)
    if store_id:
        q = q.where(Recommendation.store_id == store_id)
    rows = (await db.execute(q)).scalars().all()
    return {
        "recommendations": [
            {
                "id": r.id,
                "store_id": r.store_id,
                "query": r.query,
                "sku": r.sku,
                "product_name": r.product_name,
                "action": r.action,
                "delta_pct": r.delta_pct,
                "rationale": r.rationale,
                "confidence": r.confidence,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }
