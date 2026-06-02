from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import ExternalSignal, Forecast, Product, Recommendation, Store, Transaction


async def compute_store_health(session: AsyncSession) -> list[dict]:
    stores = (await session.execute(select(Store).where(Store.is_active == True))).scalars().all()
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    results = []
    for store in stores:
        forecast_fresh = (
            await session.execute(
                select(func.max(Forecast.created_at))
                .join(Product, Product.id == Forecast.product_id)
                .where(Product.store_id == store.id)
            )
        ).scalar()
        signal_count = (
            await session.execute(select(func.count(ExternalSignal.id)))
        ).scalar() or 0

        txn_recent = (
            await session.execute(
                select(func.count(Transaction.id)).where(
                    Transaction.store_id == store.id, Transaction.sold_at >= week_ago
                )
            )
        ).scalar() or 0
        txn_prev = (
            await session.execute(
                select(func.count(Transaction.id)).where(
                    Transaction.store_id == store.id,
                    Transaction.sold_at >= two_weeks_ago,
                    Transaction.sold_at < week_ago,
                )
            )
        ).scalar() or 0

        rec_count = (
            await session.execute(
                select(func.count(Recommendation.id)).where(
                    Recommendation.store_id == store.id, Recommendation.created_at >= week_ago
                )
            )
        ).scalar() or 0

        days_since_forecast = 7.0
        if forecast_fresh:
            days_since_forecast = max(0, (now - forecast_fresh.replace(tzinfo=timezone.utc)).days)

        forecast_score = max(0, 100 - days_since_forecast * 10)
        signal_score = min(100, signal_count * 15)
        txn_trend = ((txn_recent - txn_prev) / txn_prev * 100) if txn_prev else (100 if txn_recent else 0)
        txn_score = min(100, max(0, 50 + txn_trend / 2))
        engagement_score = min(100, rec_count * 25)

        overall = round(
            forecast_score * 0.25 + signal_score * 0.25 + txn_score * 0.25 + engagement_score * 0.25
        )

        results.append(
            {
                "store_id": store.id,
                "store_name": store.name,
                "location": store.location,
                "health_score": overall,
                "forecast_score": round(forecast_score),
                "signal_score": round(signal_score),
                "transaction_score": round(txn_score),
                "engagement_score": round(engagement_score),
                "txn_recent": txn_recent,
                "recommendations_recent": rec_count,
            }
        )

    results.sort(key=lambda x: x["health_score"], reverse=True)
    return results
