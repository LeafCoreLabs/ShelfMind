from app.celery_app import celery_app
from app.db.session import SyncSessionLocal
from app.services.alert_evaluator import evaluate_alert_rules


@celery_app.task(name="app.tasks.admin_tasks.evaluate_alerts")
def evaluate_alerts_task() -> dict:
    session = SyncSessionLocal()
    try:
        count = evaluate_alert_rules(session)
        return {"alerts_created": count}
    finally:
        session.close()


@celery_app.task(name="app.tasks.admin_tasks.snapshot_forecast_accuracy")
def snapshot_forecast_accuracy_task() -> dict:
    import asyncio

    from app.db.session import AsyncSessionLocal
    from app.services.forecast_accuracy import save_accuracy_snapshots

    async def run():
        async with AsyncSessionLocal() as session:
            return await save_accuracy_snapshots(session)

    count = asyncio.run(run())
    return {"snapshots_created": count}
