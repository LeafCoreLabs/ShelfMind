import csv
import io
from datetime import datetime, timezone

import boto3
from botocore.client import Config
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_owner_store_id, require_store_owner
from app.db.session import get_db
from app.models.store import Forecast, Product, Transaction

router = APIRouter(dependencies=[Depends(require_store_owner)])


@router.post("/reports/export")
async def export_report(db: AsyncSession = Depends(get_db), store_id: int = Depends(get_owner_store_id)):
    rows = (
        await db.execute(
            select(Forecast, Product)
            .join(Product, Product.id == Forecast.product_id)
            .where(Product.store_id == store_id)
            .order_by(Forecast.forecast_date, Product.sku)
        )
    ).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["sku", "product_name", "category", "forecast_date", "predicted_qty", "confidence"])
    for f, p in rows:
        writer.writerow([p.sku, p.name, p.category, f.forecast_date, f.predicted_qty, f.confidence])
    settings = get_settings()
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
    )
    key = f"reports/store-{store_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.csv"
    s3.put_object(Bucket=settings.s3_bucket, Key=key, Body=output.getvalue().encode(), ContentType="text/csv")
    url = s3.generate_presigned_url("get_object", Params={"Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=3600)
    return {"key": key, "download_url": url}


@router.post("/reports/import-csv")
async def import_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    imported = 0
    sku_cache: dict[str, Product] = {}
    for p in (await db.execute(select(Product).where(Product.store_id == store_id))).scalars().all():
        sku_cache[p.sku] = p
    for row in reader:
        sku = row.get("sku", "").strip()
        if not sku:
            continue
        product = sku_cache.get(sku)
        if not product:
            product = Product(store_id=store_id, sku=sku, name=row.get("product_name", sku), category=row.get("category", "General"))
            db.add(product)
            await db.flush()
            sku_cache[sku] = product
        sold_at = datetime.fromisoformat(row["sold_at"].replace("Z", "+00:00"))
        db.add(
            Transaction(
                store_id=store_id,
                product_id=product.id,
                quantity=int(row.get("quantity", 1)),
                unit_price=float(row.get("unit_price", 0)),
                sold_at=sold_at,
            )
        )
        imported += 1
    await db.commit()
    return {"imported": imported}
