from fastapi import APIRouter

from app.api.routes.admin import (
    ai,
    ai,
    alerts,
    analytics,
    anomalies,
    audit_reports,
    benchmarks_hub,
    copilot,
    forecast_health,
    jobs,
    onboarding,
    restock,
    signals_hub,
    store_health,
    stores,
    system_health,
    users,
)

router = APIRouter()
router.include_router(analytics.router)
router.include_router(signals_hub.router)
router.include_router(store_health.router)
router.include_router(benchmarks_hub.router)
router.include_router(forecast_health.router)
router.include_router(anomalies.router)
router.include_router(copilot.router)
router.include_router(ai.router)
router.include_router(alerts.router)
router.include_router(restock.router)
router.include_router(audit_reports.router)
router.include_router(users.router)
router.include_router(stores.router)
router.include_router(onboarding.router)
router.include_router(jobs.router)
router.include_router(system_health.router)
