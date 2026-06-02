from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_owner_store_id, require_store_owner
from app.db.session import get_db
from app.models.store import Product
from app.services.commerce_ops import adjust_product_stock

router = APIRouter(dependencies=[Depends(require_store_owner)])


class ProductUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    list_price: float | None = None
    cost_price: float | None = None
    stock_on_hand: int | None = None
    reorder_level: int | None = None


class StockAdjust(BaseModel):
    delta: int


@router.get("/inventory/products")
async def list_products(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    rows = (await db.execute(select(Product).where(Product.store_id == store_id).order_by(Product.sku))).scalars().all()
    return {
        "products": [
            {
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
                "list_price": p.list_price,
                "cost_price": p.cost_price,
                "stock_on_hand": p.stock_on_hand,
                "reorder_level": p.reorder_level,
                "low_stock": p.stock_on_hand <= p.reorder_level,
            }
            for p in rows
        ]
    }


@router.get("/inventory/low-stock")
async def low_stock(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    rows = (
        await db.execute(
            select(Product).where(Product.store_id == store_id, Product.stock_on_hand <= Product.reorder_level)
        )
    ).scalars().all()
    return {"products": [{"id": p.id, "sku": p.sku, "name": p.name, "stock_on_hand": p.stock_on_hand} for p in rows]}


@router.patch("/inventory/products/{product_id}")
async def update_product(
    product_id: int,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    product = (
        await db.execute(select(Product).where(Product.id == product_id, Product.store_id == store_id))
    ).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(product, field, val)
    await db.commit()
    return {"updated": True}


@router.post("/inventory/products/{product_id}/adjust-stock")
async def adjust_stock(
    product_id: int,
    body: StockAdjust,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    return await adjust_product_stock(db, store_id, product_id, body.delta)
