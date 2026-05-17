# Grand Contract v1.0 — M11 Audit Service
from __future__ import annotations
from uuid import UUID
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
    # TODO: implement per contract
    pass


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
    # TODO: implement per contract
    pass
