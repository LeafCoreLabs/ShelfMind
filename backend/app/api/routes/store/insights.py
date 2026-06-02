from datetime import datetime, timedelta, timezone
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_owner_store_id, require_store_owner
from app.db.session import get_db
from app.models.admin import AlertEvent
from app.models.store import ExternalSignal, Forecast, Product, Recommendation, Store, Transaction
from app.services.anomaly_detector import detect_anomalies
from app.services.admin_nl_query import explain_insight
from app.services.collaborative import get_store_benchmarks
from app.services.forecast_accuracy import compute_forecast_accuracy
from app.services.nl_query import process_nl_query
from app.services.weather_forecast import fetch_store_weather

router = APIRouter(dependencies=[Depends(require_store_owner)])


async def _load_store_weather(store: Store | None, store_id: int) -> dict | None:
    if not store:
        return None
    return await asyncio.to_thread(
        fetch_store_weather,
        store.lat,
        store.lon,
        store.location or "",
        store.timezone or "Asia/Kolkata",
        store_id,
    )


class QueryBody(BaseModel):
    query: str


class ExplainBody(BaseModel):
    title: str
    detail: str
    insight_type: str = "anomaly"


async def _store_categories(db: AsyncSession, store_id: int) -> set[str]:
    rows = (await db.execute(select(Product.category).where(Product.store_id == store_id).distinct())).scalars().all()
    return set(rows)


@router.get("/overview")
async def store_overview(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    from app.models.commerce import Customer, Invoice

    store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one_or_none()
    categories = await _store_categories(db, store_id)

    low_stock = (
        await db.execute(
            select(func.count(Product.id)).where(
                Product.store_id == store_id, Product.stock_on_hand <= Product.reorder_level
            )
        )
    ).scalar() or 0
    revenue = (
        await db.execute(
            select(func.sum(Transaction.quantity * Transaction.unit_price)).where(Transaction.store_id == store_id)
        )
    ).scalar() or 0
    unpaid = (
        await db.execute(
            select(func.count(Invoice.id)).where(Invoice.store_id == store_id, Invoice.status.in_(["sent", "overdue"]))
        )
    ).scalar() or 0
    unacked_alerts = (
        await db.execute(
            select(func.count(AlertEvent.id)).where(
                AlertEvent.store_id == store_id, AlertEvent.acknowledged.is_(False)
            )
        )
    ).scalar() or 0
    anomalies = await detect_anomalies(db, store_id=store_id)

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    weekly_revenue = (
        await db.execute(
            select(func.sum(Transaction.quantity * Transaction.unit_price)).where(
                Transaction.store_id == store_id, Transaction.sold_at >= week_ago
            )
        )
    ).scalar() or 0

    top_product_row = (
        await db.execute(
            select(Product.name, func.sum(Transaction.quantity * Transaction.unit_price).label("rev"))
            .join(Transaction, Transaction.product_id == Product.id)
            .where(Transaction.store_id == store_id, Transaction.sold_at >= week_ago)
            .group_by(Product.id)
            .order_by(func.sum(Transaction.quantity * Transaction.unit_price).desc())
            .limit(1)
        )
    ).first()
    top_seller = top_product_row[0] if top_product_row else None

    sig_rows = (
        await db.execute(select(ExternalSignal).order_by(ExternalSignal.created_at.desc()).limit(20))
    ).scalars().all()
    top_local_signal = None
    for s in sig_rows:
        if not s.category or s.category in categories:
            top_local_signal = {
                "title": s.signal_type.replace("_", " ").title(),
                "description": s.description,
                "category": s.category,
            }
            break

    urgent_actions: list[dict] = []
    if low_stock > 0:
        urgent_actions.append({"type": "low_stock", "label": f"{low_stock} items need restocking", "href": "/store/inventory"})
    if unacked_alerts > 0:
        urgent_actions.append({"type": "alerts", "label": f"{unacked_alerts} alerts need your attention", "href": "/store/alerts"})
    if unpaid > 0:
        urgent_actions.append({"type": "bills", "label": f"{unpaid} unpaid bills waiting", "href": "/store/billing"})
    if anomalies:
        urgent_actions.append(
            {
                "type": "demand",
                "label": f"{len(anomalies)} unusual demand pattern{'s' if len(anomalies) != 1 else ''}",
                "href": "/store/insights",
            }
        )

    relevant_signals = sum(
        1 for s in sig_rows if not s.category or s.category in categories
    )

    weather = await _load_store_weather(store, store_id)
    if weather and weather.get("retail_signals"):
        ws = weather["retail_signals"][0]
        top_local_signal = {
            "title": f"Live weather — {weather['current']['condition']}",
            "description": ws["description"],
            "category": ws["category"],
        }

    return {
        "store_id": store_id,
        "store_name": store.name if store else "",
        "store_location": store.location if store else "",
        "product_count": (await db.execute(select(func.count(Product.id)).where(Product.store_id == store_id))).scalar() or 0,
        "low_stock_count": low_stock,
        "customer_count": (await db.execute(select(func.count(Customer.id)).where(Customer.store_id == store_id))).scalar() or 0,
        "total_revenue": round(float(revenue), 2),
        "weekly_revenue": round(float(weekly_revenue), 2),
        "top_seller": top_seller,
        "unpaid_invoices": unpaid,
        "unacked_alerts": unacked_alerts,
        "forecasts_available": (
            await db.execute(select(func.count(Forecast.id)).join(Product).where(Product.store_id == store_id))
        ).scalar()
        or 0,
        "anomaly_count": len(anomalies),
        "signals_active": relevant_signals,
        "ai_queries": (
            await db.execute(select(func.count(Recommendation.id)).where(Recommendation.store_id == store_id))
        ).scalar()
        or 0,
        "top_local_signal": top_local_signal,
        "urgent_actions": urgent_actions,
        "weather": weather,
    }


@router.get("/insights/summary")
async def insights_summary(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    top_products = (
        await db.execute(
            select(
                Product.sku,
                Product.name,
                Product.category,
                func.sum(Transaction.quantity).label("total_qty"),
                func.sum(Transaction.quantity * Transaction.unit_price).label("revenue"),
            )
            .join(Transaction, Transaction.product_id == Product.id)
            .where(Product.store_id == store_id)
            .group_by(Product.id)
            .order_by(func.sum(Transaction.quantity * Transaction.unit_price).desc())
            .limit(5)
        )
    ).all()
    categories = (
        await db.execute(
            select(Product.category, func.sum(Transaction.quantity).label("qty"))
            .join(Transaction, Transaction.product_id == Product.id)
            .where(Transaction.store_id == store_id)
            .group_by(Product.category)
            .order_by(func.sum(Transaction.quantity).desc())
        )
    ).all()
    forecast_count = (
        await db.execute(select(func.count(Forecast.id)).join(Product).where(Product.store_id == store_id))
    ).scalar() or 0
    query_count = (
        await db.execute(select(func.count(Recommendation.id)).where(Recommendation.store_id == store_id))
    ).scalar() or 0
    revenue = (
        await db.execute(
            select(func.sum(Transaction.quantity * Transaction.unit_price)).where(Transaction.store_id == store_id)
        )
    ).scalar() or 0
    return {
        "store_id": store_id,
        "top_products": [
            {"sku": r.sku, "name": r.name, "category": r.category, "total_qty": int(r.total_qty or 0), "revenue": round(float(r.revenue or 0), 2)}
            for r in top_products
        ],
        "category_trends": [{"category": r.category, "quantity": int(r.qty or 0)} for r in categories],
        "signals_active": (await db.execute(select(func.count(ExternalSignal.id)))).scalar() or 0,
        "forecasts_available": forecast_count,
        "query_count": query_count,
        "weekly_revenue": round(float(revenue), 2),
    }


@router.get("/insights/forecasts")
async def insights_forecasts(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    rows = (
        await db.execute(
            select(Forecast, Product)
            .join(Product, Product.id == Forecast.product_id)
            .where(Product.store_id == store_id)
            .order_by(Forecast.forecast_date, Product.sku)
        )
    ).all()
    return {
        "forecasts": [
            {
                "sku": p.sku,
                "product_name": p.name,
                "category": p.category,
                "date": str(f.forecast_date),
                "predicted_qty": f.predicted_qty,
                "lower_bound": f.lower_bound,
                "upper_bound": f.upper_bound,
                "confidence": f.confidence,
            }
            for f, p in rows
        ]
    }


@router.get("/insights/heatmap")
async def insights_heatmap(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    rows = (
        await db.execute(
            select(
                Product.category,
                func.extract("hour", Transaction.sold_at).label("hour"),
                func.sum(Transaction.quantity).label("qty"),
            )
            .join(Product, Product.id == Transaction.product_id)
            .where(Transaction.store_id == store_id)
            .group_by(Product.category, func.extract("hour", Transaction.sold_at))
        )
    ).all()
    data: dict[str, dict[int, int]] = {}
    for row in rows:
        if row.category not in data:
            data[row.category] = {h: 0 for h in range(24)}
        data[row.category][int(row.hour)] = int(row.qty)
    return {
        "heatmap": [
            {"category": cat, "hours": [{"hour": h, "value": vals[h]} for h in range(24)]}
            for cat, vals in data.items()
        ]
    }


@router.get("/weather")
async def store_weather(
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
    refresh: bool = False,
):
    store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    weather = await asyncio.to_thread(
        fetch_store_weather,
        store.lat,
        store.lon,
        store.location or "",
        store.timezone or "Asia/Kolkata",
        store_id,
        not refresh,
    )
    return weather


@router.get("/insights/signals")
async def insights_signals(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one_or_none()
    categories = await _store_categories(db, store_id)
    rows = (await db.execute(select(ExternalSignal).order_by(ExternalSignal.created_at.desc()).limit(30))).scalars().all()
    signals = []
    weather = await _load_store_weather(store, store_id)
    if weather:
        for ws in weather.get("retail_signals", []):
            if ws.get("category") in categories or not categories:
                signals.append(
                    {
                        "id": f"weather-{ws['category']}",
                        "signal_type": "live_weather",
                        "category": ws["category"],
                        "description": ws["description"],
                        "title": f"Live forecast — {ws['category']}",
                        "impact": ws.get("impact", "medium"),
                        "source": weather.get("source", "live"),
                    }
                )
    for s in rows:
        if s.category and s.category not in categories:
            continue
        signals.append(
            {
                "id": s.id,
                "signal_type": s.signal_type,
                "category": s.category,
                "description": s.description,
                "title": s.signal_type.replace("_", " ").title(),
            }
        )
    return {
        "signals": signals[:10],
        "store_location": store.location if store else "",
        "weather": weather,
    }


@router.get("/insights/benchmarks")
async def insights_benchmarks(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    benchmarks = await get_store_benchmarks(db, store_id)
    return {"benchmarks": benchmarks}


@router.get("/insights/accuracy")
async def insights_accuracy(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    return await compute_forecast_accuracy(db, store_id=store_id)


@router.get("/insights/anomalies")
async def insights_anomalies(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    anomalies = await detect_anomalies(db, store_id=store_id)
    return {"anomalies": anomalies, "count": len(anomalies)}


@router.post("/ai/query")
async def ai_query(body: QueryBody, db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    return await process_nl_query(db, body.query, store_id)


@router.post("/ai/explain")
async def ai_explain(body: ExplainBody, db: AsyncSession = Depends(get_db)):
    return await explain_insight(db, body.title, body.detail, body.insight_type)


@router.get("/alerts")
async def store_alerts(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    rows = (
        await db.execute(
            select(AlertEvent)
            .where(AlertEvent.store_id == store_id)
            .order_by(AlertEvent.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return {
        "alerts": [
            {"id": a.id, "severity": a.severity, "title": a.title, "message": a.message, "acknowledged": a.acknowledged}
            for a in rows
        ]
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_store_alert(alert_id: int, db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    alert = (await db.execute(select(AlertEvent).where(AlertEvent.id == alert_id))).scalar_one_or_none()
    if not alert or alert.store_id != store_id:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = True
    await db.commit()
    return {"acknowledged": True}
