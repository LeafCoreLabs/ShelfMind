import json
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import ExternalSignal, Forecast, Product, Recommendation, Store
from app.services.collaborative import get_peer_context
from app.services.llm import chat_json
from app.services.store_health import compute_store_health


def _admin_demo(context: dict, query: str) -> dict:
    store_names = [s["name"] for s in context.get("stores", [])[:2]]
    s1 = store_names[0] if store_names else "Demo Store"
    s2 = store_names[1] if len(store_names) > 1 else s1
    return {
        "answer": f"ML models flag elevated umbrella demand at {s1} driven by monsoon signals. Beverages spiking at {s2} ahead of weekend heatwave.",
        "insights": [
            {"store": s1, "risk": "Umbrella stockout in 4 days", "confidence": 0.91},
            {"store": s2, "risk": "Beverage demand +120% weekend", "confidence": 0.87},
        ],
        "recommendations": [
            {"action": "Bulk restock umbrellas across western region stores", "priority": "high"},
            {"action": "Increase cold beverage allocation for weekend heatwave", "priority": "medium"},
        ],
        "query": query,
    }


async def _admin_context(session: AsyncSession) -> dict:
    stores = (await session.execute(select(Store).where(Store.is_active == True))).scalars().all()
    health = await compute_store_health(session)
    signals = (
        await session.execute(select(ExternalSignal).order_by(ExternalSignal.created_at.desc()).limit(15))
    ).scalars().all()
    week_end = date.today() + timedelta(days=7)
    forecasts = (
        await session.execute(
            select(Forecast, Product, Store)
            .join(Product, Product.id == Forecast.product_id)
            .join(Store, Store.id == Product.store_id)
            .where(Forecast.forecast_date <= week_end)
            .order_by(Forecast.predicted_qty.desc())
            .limit(20)
        )
    ).all()

    from app.db.session import SyncSessionLocal

    sync = SyncSessionLocal()
    try:
        peers = get_peer_context(sync)
    finally:
        sync.close()

    return {
        "stores": [{"id": s.id, "name": s.name, "location": s.location} for s in stores],
        "health": health[:10],
        "signals": [{"type": s.signal_type, "category": s.category, "description": s.description} for s in signals],
        "forecasts": [
            {"store": st.name, "sku": p.sku, "name": p.name, "date": str(f.forecast_date), "qty": f.predicted_qty}
            for f, p, st in forecasts
        ],
        "peers": peers,
    }


async def process_admin_query(session: AsyncSession, query: str) -> dict:
    context = await _admin_context(session)
    fallback = _admin_demo(context, query)

    prompt = f"""You are ShelfMind Admin Copilot — an AI assistant for a multi-store retail ML platform.
Use Prophet forecasts, external signals (weather/events/trends), and store health scores to answer platform-wide questions.

Question: {query}

Context:
{json.dumps(context, indent=2)}

Respond ONLY with valid JSON:
{{"answer": "2-4 sentence summary", "insights": [{{"store": "...", "risk": "...", "confidence": 0.0-1.0}}], "recommendations": [{{"action": "...", "priority": "high|medium|low"}}]}}"""

    result = chat_json(prompt, fallback)
    result["query"] = query

    session.add(
        Recommendation(
            store_id=context["stores"][0]["id"] if context["stores"] else 1,
            query=f"[ADMIN] {query}",
            sku="PLATFORM",
            product_name="Admin Copilot",
            action="insight",
            delta_pct=0,
            rationale=result.get("answer", "")[:500],
            confidence=0.85,
        )
    )
    await session.commit()
    return result


async def explain_insight(session: AsyncSession, title: str, detail: str, insight_type: str = "anomaly") -> dict:
    context = await _admin_context(session)
    fallback = {
        "explanation": f"This {insight_type} ({title}) is likely driven by local demand signals and forecast drift. {detail}",
        "recommended_action": "Review affected SKU forecasts and adjust restock orders within 48 hours.",
    }

    prompt = f"""You are ShelfMind ML analyst. Explain this {insight_type} to a retail platform admin in plain language.

Title: {title}
Detail: {detail}

Platform context:
{json.dumps(context, indent=2)}

Respond ONLY with valid JSON:
{{"explanation": "2-3 sentences", "recommended_action": "one concrete action"}}"""

    return chat_json(prompt, fallback)
