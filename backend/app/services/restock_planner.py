from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import ExternalSignal, Forecast, Product, Recommendation, Store


async def generate_restock_plan(
    session: AsyncSession, store_ids: list[int] | None = None, categories: list[str] | None = None
) -> list[dict]:
    q = (
        select(Forecast, Product, Store)
        .join(Product, Product.id == Forecast.product_id)
        .join(Store, Store.id == Product.store_id)
        .where(Store.is_active == True)
        .order_by(Forecast.predicted_qty.desc())
    )
    if store_ids:
        q = q.where(Store.id.in_(store_ids))
    if categories:
        q = q.where(Product.category.in_(categories))

    rows = (await session.execute(q.limit(50))).all()
    signals = (await session.execute(select(ExternalSignal).order_by(ExternalSignal.created_at.desc()).limit(10))).scalars().all()

    plan = []
    seen: set[tuple[int, str]] = set()
    for forecast, product, store in rows:
        key = (store.id, product.sku)
        if key in seen:
            continue
        seen.add(key)

        signal_boost = 0.0
        for sig in signals:
            if sig.category.lower() in product.category.lower() or product.category.lower() in sig.category.lower():
                signal_boost += sig.value * 10

        base = float(forecast.predicted_qty)
        delta_pct = round(min(400, max(-50, (base / max(base - signal_boost, 1) - 1) * 100 + signal_boost)))
        if delta_pct == 0:
            delta_pct = 15 if base > 5 else 0
        action = "increase" if delta_pct > 0 else "decrease" if delta_pct < 0 else "hold"

        rationale = f"7-day forecast {base:.0f} units"
        if signal_boost:
            rationale += f"; local signals adjust +{signal_boost:.0f}%"

        plan.append(
            {
                "store_id": store.id,
                "store_name": store.name,
                "sku": product.sku,
                "product_name": product.name,
                "category": product.category,
                "action": action,
                "delta_pct": delta_pct,
                "rationale": rationale,
                "confidence": round(float(forecast.confidence), 2),
            }
        )

    return plan


async def publish_restock_plan(session: AsyncSession, plan: list[dict], query: str = "Admin restock plan") -> int:
    count = 0
    for item in plan:
        session.add(
            Recommendation(
                store_id=item["store_id"],
                query=query,
                sku=item["sku"],
                product_name=item["product_name"],
                action=item["action"],
                delta_pct=item["delta_pct"],
                rationale=item["rationale"],
                confidence=item["confidence"],
            )
        )
        count += 1
    await session.commit()
    return count
