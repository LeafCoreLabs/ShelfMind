import time
from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import engine as async_engine

router = APIRouter()

_start_time = time.time()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "shelfmind-backend"}


@router.get("/health/deep")
async def deep_health():
    checks: dict[str, str] = {}
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    try:
        from app.config import get_settings
        import redis

        settings = get_settings()
        r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    uptime = round(time.time() - _start_time, 1)
    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "service": "shelfmind-backend",
        "uptime_seconds": uptime,
        "checks": checks,
    }
