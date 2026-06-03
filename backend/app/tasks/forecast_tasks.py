import csv
import io
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.db.session import SyncSessionLocal
from app.services.collaborative import generate_peer_benchmarks
from app.services.forecast import run_all_forecasts
from app.services.s3_reports import upload_report_csv
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

        key = f"reports/weekly-{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
        result = upload_report_csv(key, output.getvalue().encode())
        return {"key": result["key"], "url": result["download_url"], "storage": result["storage"]}
    finally:
        session.close()
