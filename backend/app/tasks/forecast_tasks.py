import csv
import io
from datetime import datetime, timezone

import boto3
from botocore.client import Config

from app.celery_app import celery_app
from app.config import get_settings
from app.db.session import SyncSessionLocal
from app.services.collaborative import generate_peer_benchmarks
from app.services.forecast import run_all_forecasts
from app.models.store import Forecast, Product, Transaction
from sqlalchemy import func, select


@celery_app.task(name="app.tasks.forecast_tasks.run_prophet_forecasts")
def run_prophet_forecasts() -> dict:
    session = SyncSessionLocal()
    try:
        count = run_all_forecasts(session)
        return {"forecasts_created": count}
    finally:
        session.close()


@celery_app.task(name="app.tasks.forecast_tasks.generate_peer_benchmarks")
def generate_peer_benchmarks_task() -> dict:
    session = SyncSessionLocal()
    try:
        count = generate_peer_benchmarks(session)
        return {"benchmarks_created": count}
    finally:
        session.close()


@celery_app.task(name="app.tasks.forecast_tasks.export_scheduled_reports")
def export_scheduled_reports() -> dict:
    session = SyncSessionLocal()
    try:
        rows = session.execute(
            select(
                Product.sku,
                Product.name,
                Product.category,
                Forecast.forecast_date,
                Forecast.predicted_qty,
                Forecast.confidence,
            )
            .join(Forecast, Forecast.product_id == Product.id)
            .order_by(Forecast.forecast_date, Product.sku)
        ).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["sku", "name", "category", "forecast_date", "predicted_qty", "confidence"])
        for row in rows:
            writer.writerow(list(row))

        settings = get_settings()
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4"),
        )
        key = f"reports/weekly-{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
        s3.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=output.getvalue().encode(),
            ContentType="text/csv",
        )
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=3600,
        )
        return {"key": key, "url": url}
    finally:
        session.close()
