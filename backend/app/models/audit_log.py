# Grand Contract v1.0 — M11 Audit Log ORM model
import uuid
import enum
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Enum, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class AuditAction(str, enum.Enum):
    WORKSPACE_CREATED = "WORKSPACE_CREATED"
    PROJECT_CREATED = "PROJECT_CREATED"
    VIDEO_UPLOADED = "VIDEO_UPLOADED"
    VIDEO_PROCESSING_STARTED = "VIDEO_PROCESSING_STARTED"
    VIDEO_PROCESSING_COMPLETED = "VIDEO_PROCESSING_COMPLETED"
    VIDEO_MARKUP_STARTED = "VIDEO_MARKUP_STARTED"
    VIDEO_MARKUP_COMPLETED = "VIDEO_MARKUP_COMPLETED"
    LINE_DRAWN = "LINE_DRAWN"
    RESULTS_DOWNLOADED = "RESULTS_DOWNLOADED"
    QUEUE_CONTROLLED = "QUEUE_CONTROLLED"
    WORKER_SCALED = "WORKER_SCALED"


class AuditLog(Base):
    """
    Immutable audit record for all workflow actions.

    Invariants:
        - created_at is set by DB server default (tamper-resistant)
        - user_id may be null only for system-initiated actions (watcher)
        - records are never deleted — append-only
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
