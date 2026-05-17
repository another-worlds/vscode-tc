# Grand Contract v1.0 — M8 Counting Line ORM models
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class CountingLine(Base):
    """
    A user-drawn line on a video for vehicle counting.

    points: list of [x, y] pixel coordinates forming the line.
    Invariant: len(points) >= 2
    """
    __tablename__ = "counting_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    points: Mapped[list] = mapped_column(JSONB, nullable=False)   # [[x,y], [x,y], ...]
    color: Mapped[str] = mapped_column(String, nullable=False, default="#FF0000")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    video: Mapped["Video"] = relationship(back_populates="counting_lines")
    result: Mapped["CountingResult | None"] = relationship(back_populates="counting_line", uselist=False, cascade="all, delete-orphan")


class CountingResult(Base):
    """
    Server-computed intersection counts for a CountingLine.

    Invariant: total = count_in + count_out (computed column in DB)
    vehicle_pct: {"car": float, "truck": float, ...} summing to 100.0
    """
    __tablename__ = "counting_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    counting_line_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("counting_lines.id", ondelete="CASCADE"), nullable=False, unique=True)
    count_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    count_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vehicle_pct: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    counting_line: Mapped["CountingLine"] = relationship(back_populates="result")
