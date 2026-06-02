from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "shelfmind",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.forecast_tasks", "app.tasks.signal_tasks", "app.tasks.admin_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    beat_schedule={
        "refresh-external-signals": {
            "task": "app.tasks.signal_tasks.refresh_external_signals",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        "run-prophet-forecasts": {
            "task": "app.tasks.forecast_tasks.run_prophet_forecasts",
            "schedule": crontab(minute=0, hour=2),
        },
        "generate-peer-benchmarks": {
            "task": "app.tasks.forecast_tasks.generate_peer_benchmarks",
            "schedule": crontab(minute=0, hour=3, day_of_week=1),
        },
        "export-scheduled-reports": {
            "task": "app.tasks.forecast_tasks.export_scheduled_reports",
            "schedule": crontab(minute=0, hour=4, day_of_week=1),
        },
        "evaluate-admin-alerts": {
            "task": "app.tasks.admin_tasks.evaluate_alerts",
            "schedule": crontab(minute="*/15"),
        },
        "snapshot-forecast-accuracy": {
            "task": "app.tasks.admin_tasks.snapshot_forecast_accuracy",
            "schedule": crontab(minute=0, hour=5, day_of_week=1),
        },
    },
)
