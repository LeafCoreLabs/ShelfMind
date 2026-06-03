import time
from datetime import datetime, timezone

import boto3
import redis
from botocore.client import Config
from botocore.exceptions import ClientError
from sqlalchemy import func, select, text

from app.config import get_settings
from app.db.session import SyncSessionLocal
from app.models.store import Store, Transaction
from app.models.user import User


def _check(name: str, fn) -> dict:
    start = time.perf_counter()
    try:
        detail = fn()
        latency = round((time.perf_counter() - start) * 1000, 1)
        return {"name": name, "status": "healthy", "latency_ms": latency, "detail": detail}
    except Exception as exc:
        latency = round((time.perf_counter() - start) * 1000, 1)
        return {"name": name, "status": "down", "latency_ms": latency, "detail": str(exc)}


def collect_system_health() -> dict:
    settings = get_settings()
    checks = []

    def postgres():
        session = SyncSessionLocal()
        try:
            session.execute(text("SELECT 1"))
            stores = session.execute(select(func.count(Store.id))).scalar() or 0
            users = session.execute(select(func.count(User.id))).scalar() or 0
            txns = session.execute(select(func.count(Transaction.id))).scalar() or 0
            return {"stores": stores, "users": users, "transactions": txns}
        finally:
            session.close()

    def redis_check():
        r = redis.from_url(settings.redis_url)
        r.ping()
        return {"connected": True}

    def minio_check():
        if not settings.s3_enabled:
            return {"enabled": False, "note": "S3 disabled — reports download inline"}
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint or None,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4"),
        )
        s3.head_bucket(Bucket=settings.s3_bucket)
        return {"bucket": settings.s3_bucket, "enabled": True}

    def groq_check():
        return {
            "enabled": bool(settings.llm_api_key),
            "provider": settings.llm_provider,
            "model": settings.llm_model or "demo-fallback",
        }

    def celery_check():
        try:
            from app.celery_app import celery_app

            inspect = celery_app.control.inspect(timeout=2.0)
            active = inspect.active() or {}
            workers = list(active.keys())
            return {"workers_online": len(workers), "workers": workers[:5]}
        except Exception as exc:
            return {"workers_online": 0, "note": str(exc)}

    checks.append(_check("postgresql", postgres))
    checks.append(_check("redis", redis_check))
    if settings.s3_enabled:
        checks.append(_check("minio", minio_check))
    else:
        checks.append(
            {
                "name": "minio",
                "status": "healthy",
                "latency_ms": 0,
                "detail": {"enabled": False, "note": "S3 disabled — inline report downloads"},
            }
        )
    checks.append(_check("celery", celery_check))
    checks.append(
        {
            "name": "backend_api",
            "status": "healthy",
            "latency_ms": 0,
            "detail": {"service": "shelfmind-backend"},
        }
    )
    checks.append(_check("groq_ai", groq_check))

    statuses = [c["status"] for c in checks]
    overall = "healthy" if all(s == "healthy" for s in statuses) else "degraded" if any(s == "healthy" for s in statuses) else "down"

    return {
        "overall": overall,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
