from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import AuditLog


async def log_audit(
    session: AsyncSession,
    actor_email: str,
    action: str,
    resource: str,
    detail: dict | None = None,
) -> None:
    session.add(AuditLog(actor_email=actor_email, action=action, resource=resource, detail=detail))
    await session.commit()
