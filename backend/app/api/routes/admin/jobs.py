from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.core.deps import require_admin
from app.models.user import User
from app.tasks.forecast_tasks import (
    export_scheduled_reports,
    generate_peer_benchmarks_task,
    run_prophet_forecasts,
)
from app.tasks.signal_tasks import refresh_external_signals

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/jobs/forecasts")
async def trigger_forecasts(_: User = Depends(require_admin)):
    task = run_prophet_forecasts.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/jobs/signals")
async def trigger_signals(_: User = Depends(require_admin)):
    task = refresh_external_signals.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/jobs/benchmarks")
async def trigger_benchmarks(_: User = Depends(require_admin)):
    task = generate_peer_benchmarks_task.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/jobs/export")
async def trigger_export(_: User = Depends(require_admin)):
    task = export_scheduled_reports.delay()
    return {"task_id": task.id, "status": "queued"}


@router.get("/jobs/status/{task_id}")
async def job_status(task_id: str, _: User = Depends(require_admin)):
    result = celery_app.AsyncResult(task_id)
    return {"task_id": task_id, "state": result.state, "result": result.result if result.ready() else None}
