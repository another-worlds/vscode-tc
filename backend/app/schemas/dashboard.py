# Grand Contract v1.0 — M9 Dashboard schemas
from pydantic import BaseModel
from uuid import UUID


class WorkspaceDashboard(BaseModel):
    """
    High-level overview for a project manager.
    All durations in minutes.
    """
    workspace_id: UUID
    total_videos: int
    processed_videos: int
    pending_videos: int
    total_duration_min: float
    processed_duration_min: float
    storage_used_gb: float
    total_projects: int
    active_projects: int   # projects with unprocessed videos
    queue_depth: int       # jobs currently in Redis queue


class ProjectDashboard(BaseModel):
    """Per-project video inventory for an analyst."""
    project_id: UUID
    videos: list["VideoSummary"]


class VideoSummary(BaseModel):
    id: UUID
    filename: str
    resolution: str | None   # "1920x1080"
    size_bytes: int | None
    duration_min: float | None
    status: str
    has_counting_lines: bool
    has_results: bool
