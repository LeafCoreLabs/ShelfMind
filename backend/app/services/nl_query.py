import json
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import ExternalSignal, Forecast, Product, Recommendation
from app.services.collaborative import get_peer_context
from app.services.llm import chat_json


DEMO_RESPONSE = {
    "recommendations": [
        {
            "sku": "SKU-UMB-001",
            "product_name": "Compact Umbrella",
            "action": "increase",
            "delta_pct": 340,
            "rationale": "Umbrella demand up 340% — monsoon onset forecast.",
            "confidence": 0.91,
        },
        {
            "sku": "SKU-BEV-001",
            "product_name": "Cold Beverage 500ml",
            "action": "increase",
            "delta_pct": 100,
            "rationale": "Increase cold beverages 2x — weekend + 38°C forecast.",
            "confidence": 0.87,
        },
        {
            "sku": "SKU-NOD-001",
            "product_name": "Instant Noodles Pack",
            "action": "decrease",
            "delta_pct": -35,
            "rationale": "Reduce instant noodles — local college hostel closed for holidays.",
            "confidence": 0.84,
        },
    ]
}


async def _gather_context(session: AsyncSession, store_id: int) -> dict:
    today = date.today()
    week_end = today + timedelta(days=7)

    forecasts = (
        await session.execute(
            select(Forecast, Product)
            .join(Product, Product.id == Forecast.product_id)
            .where(Product.store_id == store_id, Forecast.forecast_date <= week_end)
            .order_by(Forecast.predicted_qty.desc())
            .limit(15)
        )
    ).all()

    signals = (
        await session.execute(select(ExternalSignal).order_by(ExternalSignal.created_at.desc()).limit(10))
    ).scalars().all()

    forecast_ctx = [
        {
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "date": str(f.forecast_date),
            "predicted_qty": f.predicted_qty,
            "confidence": f.confidence,
        }
        for f, p in forecasts
    ]

    signal_ctx = [
        {"type": s.signal_type, "category": s.category, "value": s.value, "description": s.description}
        for s in signals
    ]

    from app.db.session import SyncSessionLocal

    sync = SyncSessionLocal()
    try:
        peer_ctx = get_peer_context(sync)
    finally:
        sync.close()

    return {"forecasts": forecast_ctx, "signals": signal_ctx, "peers": peer_ctx}


async def process_nl_query(session: AsyncSession, query: str, store_id: int = 1) -> dict:
    context = await _gather_context(session, store_id)

    prompt = f"""You are ShelfMind, an AI retail inventory advisor powered by ML forecasts and local demand signals.
Given store data, answer the owner's question with specific SKU-level stocking recommendations.

Question: {query}

Context:
{json.dumps(context, indent=2)}

Respond ONLY with valid JSON:
{{"recommendations": [{{"sku": "...", "product_name": "...", "action": "increase|decrease|hold", "delta_pct": number, "rationale": "...", "confidence": 0.0-1.0}}]}}"""

    result = chat_json(prompt, DEMO_RESPONSE)

    for rec in result.get("recommendations", []):
        session.add(
            Recommendation(
                store_id=store_id,
                query=query,
                sku=rec.get("sku", ""),
                product_name=rec.get("product_name", ""),
                action=rec.get("action", "hold"),
                delta_pct=rec.get("delta_pct", 0),
                rationale=rec.get("rationale", ""),
                confidence=rec.get("confidence", 0.8),
            )
        )
    await session.commit()

    return result
