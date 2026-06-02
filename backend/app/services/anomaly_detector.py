from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import ExternalSignal, Forecast, Product, Store, Transaction


async def detect_anomalies(session: AsyncSession, store_id: int | None = None) -> list[dict]:
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    anomalies: list[dict] = []

    stores = (await session.execute(select(Store).where(Store.is_active == True))).scalars().all()
    if store_id is not None:
        stores = [s for s in stores if s.id == store_id]
    signals = (await session.execute(select(ExternalSignal).order_by(ExternalSignal.created_at.desc()).limit(5))).scalars().all()

    category_spikes: dict[str, list[int]] = {}

    for store in stores:
        rows = (
            await session.execute(
                select(Product.category, func.sum(Transaction.quantity).label("qty"))
                .join(Transaction, Transaction.product_id == Product.id)
                .where(Transaction.store_id == store.id, Transaction.sold_at >= week_ago)
                .group_by(Product.category)
            )
        ).all()

        for cat, qty in rows:
            forecast_avg = (
                await session.execute(
                    select(func.avg(Forecast.predicted_qty))
                    .join(Product, Product.id == Forecast.product_id)
                    .where(Product.store_id == store.id, Product.category == cat)
                )
            ).scalar() or 1
            actual = float(qty or 0)
            expected = float(forecast_avg) * 7
            if expected <= 0:
                continue
            delta_pct = round((actual - expected) / expected * 100)
            if abs(delta_pct) >= 80:
                category_spikes.setdefault(cat, []).append(store.id)
                signal_hint = next(
                    (s.description for s in signals if s.category.lower() in cat.lower() or cat.lower() in s.category.lower()),
                    "Demand pattern deviates from forecast baseline",
                )
                anomalies.append(
                    {
                        "id": f"{store.id}-{cat}",
                        "severity": "critical" if abs(delta_pct) >= 200 else "warning",
                        "title": f"{cat} demand {'spike' if delta_pct > 0 else 'drop'} at {store.name}",
                        "delta_pct": delta_pct,
                        "store_id": store.id,
                        "store_name": store.name,
                        "category": cat,
                        "signal_cause": signal_hint,
                        "recommended_action": "Increase stock" if delta_pct > 0 else "Reduce reorder quantity",
                    }
                )

    for cat, store_ids in category_spikes.items():
        if len(store_ids) >= 2:
            anomalies.append(
                {
                    "id": f"network-{cat}",
                    "severity": "critical",
                    "title": f"Network-wide {cat} anomaly across {len(store_ids)} stores",
                    "delta_pct": max(a["delta_pct"] for a in anomalies if a.get("category") == cat and "network" not in str(a.get("id", ""))),
                    "store_ids": store_ids,
                    "category": cat,
                    "signal_cause": next((s.description for s in signals if cat.lower() in s.category.lower()), "Multi-store correlated shift"),
                    "recommended_action": f"Review {cat} restock plan platform-wide",
                }
            )

    anomalies.sort(key=lambda x: abs(x.get("delta_pct", 0)), reverse=True)
    return anomalies[:20]
