from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.store import PeerBenchmark, Product, Transaction

PEER_DATA = [
    ("SKU-UMB-001", "Rain Gear", 12.0, 3.5),
    ("SKU-BEV-001", "Beverages", 45.0, 22.0),
    ("SKU-BEV-002", "Beverages", 38.0, 18.0),
    ("SKU-NOD-001", "Snacks", 28.0, 15.0),
    ("SKU-SNK-001", "Snacks", 20.0, 12.0),
    ("SKU-DAI-001", "Dairy", 25.0, 14.0),
]


def generate_peer_benchmarks(session: Session) -> int:
    session.execute(delete(PeerBenchmark))
    for sku, category, peer_avg, local_avg in PEER_DATA:
        lift = ((peer_avg - local_avg) / local_avg * 100) if local_avg else 0
        session.add(
            PeerBenchmark(
                category=category,
                sku=sku,
                peer_avg_daily=peer_avg,
                local_avg_daily=local_avg,
                lift_pct=round(lift, 1),
            )
        )
    session.commit()
    return len(PEER_DATA)


def get_peer_context(session: Session) -> list[dict]:
    rows = session.execute(select(PeerBenchmark)).scalars().all()
    return [
        {
            "sku": r.sku,
            "category": r.category,
            "peer_avg_daily": r.peer_avg_daily,
            "local_avg_daily": r.local_avg_daily,
            "lift_pct": r.lift_pct,
        }
        for r in rows
    ]


async def get_store_benchmarks(db: AsyncSession, store_id: int) -> list[dict]:
    """Compute peer comparison from demo store transaction history."""
    days = 90
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        await db.execute(
            select(
                Product.sku,
                Product.category,
                Transaction.store_id,
                func.sum(Transaction.quantity).label("qty"),
            )
            .join(Transaction, Transaction.product_id == Product.id)
            .where(Transaction.sold_at >= cutoff)
            .group_by(Product.sku, Product.category, Transaction.store_id)
        )
    ).all()

    by_sku: dict[str, dict[int, float]] = {}
    categories: dict[str, str] = {}
    for sku, category, sid, qty in rows:
        categories[sku] = category
        by_sku.setdefault(sku, {})[sid] = float(qty or 0) / days

    store_skus = (await db.execute(select(Product.sku).where(Product.store_id == store_id))).scalars().all()
    result: list[dict] = []
    for sku in store_skus:
        store_avgs = by_sku.get(sku, {})
        local = store_avgs.get(store_id, 0)
        peer_vals = [v for sid, v in store_avgs.items() if sid != store_id]
        peer = sum(peer_vals) / len(peer_vals) if peer_vals else (local or 1)
        lift = ((peer - local) / local * 100) if local else 0
        result.append(
            {
                "sku": sku,
                "category": categories.get(sku, ""),
                "local_avg_daily": round(local, 1),
                "peer_avg_daily": round(peer, 1),
                "lift_pct": round(lift, 1),
            }
        )

    if result:
        return sorted(result, key=lambda x: abs(x["lift_pct"]), reverse=True)

    return [
        {
            "sku": sku,
            "category": cat,
            "peer_avg_daily": peer,
            "local_avg_daily": local,
            "lift_pct": round(((peer - local) / local * 100) if local else 0, 1),
        }
        for sku, cat, peer, local in PEER_DATA
    ]
