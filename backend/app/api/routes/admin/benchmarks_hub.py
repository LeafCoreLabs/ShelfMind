from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.store import PeerBenchmark, Product, Store, Transaction

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/benchmarks/hub")
async def benchmark_hub(db: AsyncSession = Depends(get_db)):
    benchmarks = (await db.execute(select(PeerBenchmark).order_by(PeerBenchmark.lift_pct.desc()))).scalars().all()
    stores = (await db.execute(select(Store).where(Store.is_active == True))).scalars().all()

    matrix = []
    for store in stores:
        for b in benchmarks:
            actual = (
                await db.execute(
                    select(func.avg(Transaction.quantity))
                    .join(Product, Product.id == Transaction.product_id)
                    .where(Product.store_id == store.id, Product.sku == b.sku)
                )
            ).scalar() or 0
            gap = round((float(actual) - b.peer_avg_daily) / max(b.peer_avg_daily, 1) * 100, 1) if b.peer_avg_daily else 0
            matrix.append(
                {
                    "store_id": store.id,
                    "store_name": store.name,
                    "category": b.category,
                    "sku": b.sku,
                    "peer_avg": b.peer_avg_daily,
                    "local_avg": b.local_avg_daily,
                    "store_actual": round(float(actual), 1),
                    "lift_pct": b.lift_pct,
                    "gap_pct": gap,
                }
            )

    underperformers = sorted(matrix, key=lambda x: x["gap_pct"])[:8]

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
            for b in benchmarks
        ],
        "matrix": matrix,
        "underperformers": underperformers,
    }
