from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import ForecastAccuracySnapshot
from app.models.store import Forecast, Product, Transaction


async def compute_forecast_accuracy(
    session: AsyncSession, store_id: int | None = None, days: int = 14
) -> dict:
    since = date.today() - timedelta(days=days)

    q = (
        select(
            Product.store_id,
            Product.category,
            Forecast.forecast_date,
            Forecast.predicted_qty,
            func.coalesce(func.sum(Transaction.quantity), 0).label("actual_qty"),
        )
        .join(Product, Product.id == Forecast.product_id)
        .outerjoin(
            Transaction,
            (Transaction.product_id == Forecast.product_id)
            & (func.date(Transaction.sold_at) == Forecast.forecast_date),
        )
        .where(Forecast.forecast_date >= since, Forecast.forecast_date <= date.today())
        .group_by(Product.store_id, Product.category, Forecast.forecast_date, Forecast.predicted_qty, Forecast.product_id)
    )
    if store_id:
        q = q.where(Product.store_id == store_id)

    rows = (await session.execute(q)).all()

    if not rows:
        return {"mape": 0, "mae": 0, "sample_size": 0, "daily": [], "by_store": []}

    errors = []
    daily_map: dict[str, list[float]] = {}
    store_map: dict[int, list[float]] = {}

    for row in rows:
        predicted = float(row.predicted_qty)
        actual = float(row.actual_qty)
        if predicted <= 0 and actual <= 0:
            continue
        ape = abs(predicted - actual) / max(actual, predicted, 1) * 100
        ae = abs(predicted - actual)
        errors.append(ape)
        day_key = str(row.forecast_date)
        daily_map.setdefault(day_key, []).append(ape)
        store_map.setdefault(row.store_id, []).append(ape)

    mape = sum(errors) / len(errors) if errors else 0
    mae = sum(abs(float(r.predicted_qty) - float(r.actual_qty)) for r in rows) / len(rows) if rows else 0

    daily = [
        {"date": d, "mape": round(sum(v) / len(v), 1)}
        for d, v in sorted(daily_map.items())
    ]

    by_store = []
    for sid, errs in store_map.items():
        by_store.append({"store_id": sid, "mape": round(sum(errs) / len(errs), 1), "sample_size": len(errs)})

    drift_alerts = [s for s in by_store if s["mape"] > 35]

    return {
        "mape": round(mape, 1),
        "mae": round(mae, 2),
        "sample_size": len(errors),
        "daily": daily,
        "by_store": by_store,
        "drift_alerts": drift_alerts,
    }


async def save_accuracy_snapshots(session: AsyncSession) -> int:
    from app.models.store import Store

    stores = (await session.execute(select(Store.id).where(Store.is_active == True))).scalars().all()
    today = date.today()
    count = 0
    for sid in stores:
        data = await compute_forecast_accuracy(session, store_id=sid)
        session.add(
            ForecastAccuracySnapshot(
                store_id=sid,
                category="all",
                mape=data["mape"],
                mae=data["mae"],
                sample_size=data["sample_size"],
                snapshot_date=today,
            )
        )
        count += 1
    await session.commit()
    return count
