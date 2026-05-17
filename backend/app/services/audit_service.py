# Grand Contract v1.0 — M11 Audit Service
from __future__ import annotations
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog, AuditAction


async def log_action(
    action: AuditAction,
    db: AsyncSession,
    user_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Append an immutable audit record.

    Invariant: created_at set by DB server (not application) to prevent tampering.
    Side-effects: DB INSERT only (never UPDATE/DELETE).
    Performance: fire-and-forget acceptable; caller should not await in hot path.
    """
    audit = AuditLog(
        action=action,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata,
    )
    db.add(audit)
    await db.commit()


async def get_audit_log(
    db: AsyncSession,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    user_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    """
    Query audit log with optional filters.

    Returns:
        List of AuditLog records ordered by created_at DESC.
    """
    stmt = select(AuditLog)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(AuditLog.resource_id == resource_id)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)

    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()
