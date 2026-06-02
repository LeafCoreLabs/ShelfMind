from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin import AlertEvent, AlertRule
from app.models.store import Store, Transaction
from app.services.anomaly_detector import detect_anomalies


def evaluate_alert_rules(session: Session) -> int:
    rules = session.execute(select(AlertRule).where(AlertRule.is_active == True)).scalars().all()
    if not rules:
        default_rules = [
            AlertRule(name="Demand spike", rule_type="demand_spike", threshold=200),
            AlertRule(name="Low forecast confidence", rule_type="low_confidence", threshold=0.6),
            AlertRule(name="Inactive store", rule_type="inactive_store", threshold=7),
        ]
        for r in default_rules:
            session.add(r)
        session.commit()
        rules = session.execute(select(AlertRule).where(AlertRule.is_active == True)).scalars().all()

    created = 0
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    for rule in rules:
        existing = session.execute(
            select(AlertEvent).where(AlertEvent.rule_id == rule.id, AlertEvent.created_at >= since)
        ).scalars().first()
        if existing:
            continue

        if rule.rule_type == "inactive_store":
            stores = session.execute(select(Store).where(Store.is_active == True)).scalars().all()
            for store in stores:
                last_txn = session.execute(
                    select(Transaction.sold_at)
                    .where(Transaction.store_id == store.id)
                    .order_by(Transaction.sold_at.desc())
                    .limit(1)
                ).scalar()
                if last_txn and (datetime.now(timezone.utc) - last_txn.replace(tzinfo=timezone.utc)).days >= int(rule.threshold):
                    session.add(
                        AlertEvent(
                            rule_id=rule.id,
                            severity="warning",
                            title=f"Store inactive: {store.name}",
                            message=f"No transactions for {rule.threshold}+ days",
                            store_id=store.id,
                        )
                    )
                    created += 1

    session.commit()
    return created


async def evaluate_anomaly_alerts(session) -> int:
    from app.db.session import AsyncSession

    if not isinstance(session, AsyncSession):
        return 0
    anomalies = await detect_anomalies(session)
    created = 0
    for a in anomalies[:5]:
        session.add(
            AlertEvent(
                severity=a.get("severity", "warning"),
                title=a.get("title", "Anomaly detected"),
                message=a.get("recommended_action", ""),
                store_id=a.get("store_id"),
            )
        )
        created += 1
    await session.commit()
    return created
