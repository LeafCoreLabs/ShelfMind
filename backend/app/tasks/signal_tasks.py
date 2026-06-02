from datetime import datetime, timedelta, timezone

from app.celery_app import celery_app
from app.db.session import SyncSessionLocal
from app.models.store import ExternalSignal
from app.services.signals.factory import get_signal_providers


def _save_signals() -> int:
    session = SyncSessionLocal()
    try:
        now = datetime.now(timezone.utc)
        from sqlalchemy import delete
        session.execute(delete(ExternalSignal))
        count = 0
        for provider in get_signal_providers():
            for signal in provider.fetch():
                session.add(
                    ExternalSignal(
                        signal_type=signal.signal_type,
                        category=signal.category,
                        value=signal.value,
                        description=signal.description,
                        effective_from=now,
                        effective_to=now + timedelta(days=7),
                    )
                )
                count += 1
        session.commit()
        return count
    finally:
        session.close()


@celery_app.task(name="app.tasks.signal_tasks.refresh_external_signals")
def refresh_external_signals() -> dict:
    count = _save_signals()
    return {"signals_refreshed": count}
