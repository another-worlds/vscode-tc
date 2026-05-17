# Grand Contract v1.0 — M8 Counting Line schemas
from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import datetime


class LinePoint(BaseModel):
    x: float
    y: float


class CountingLineCreate(BaseModel):
    name: str
    points: list[LinePoint]
    color: str = "#FF0000"

    @field_validator("points")
    @classmethod
    def at_least_two_points(cls, v: list) -> list:
        """Invariant: a line requires >= 2 points."""
        if len(v) < 2:
            raise ValueError("counting line requires at least 2 points")
        return v


class CountingLineOut(BaseModel):
    id: UUID
    video_id: UUID
    name: str
    points: list
    color: str
    created_at: datetime
    created_by: UUID | None
    model_config = {"from_attributes": True}


class CountingResultOut(BaseModel):
    counting_line_id: UUID
    count_in: int
    count_out: int
    total: int
    vehicle_pct: dict | None
    computed_at: datetime
    model_config = {"from_attributes": True}
