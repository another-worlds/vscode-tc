# Grand Contract v1.0 — M4 Video Ingestion: Video ORM model
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, BigInteger, Float, Enum, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class VideoStatus(str, enum.Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    ERROR = "ERROR"


class Video(Base):
    """
    Represents an uploaded MP4 video.

    Status FSM: PENDING → QUEUED → PROCESSING → PROCESSED | ERROR
    Invariant:  parquet_path IS NOT NULL iff status == PROCESSED
    Invariant:  frame_count == FRAMES_SAMPLE_COUNT iff status == PROCESSED
    """
    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    filepath: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    resolution_w: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolution_h: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[VideoStatus] = mapped_column(Enum(VideoStatus), nullable=False, default=VideoStatus.PENDING)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    frame_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parquet_path: Mapped[str | None] = mapped_column(String, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="videos")
    counting_lines: Mapped[list["CountingLine"]] = relationship(back_populates="video", cascade="all, delete-orphan")
