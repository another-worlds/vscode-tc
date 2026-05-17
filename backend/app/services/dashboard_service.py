# Grand Contract v1.0 — M9 Dashboard Service
from __future__ import annotations
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.dashboard import WorkspaceDashboard, ProjectDashboard
from app.services.queue_service import get_queue_depth


async def get_workspace_dashboard(workspace_id: UUID, db: AsyncSession) -> WorkspaceDashboard:
    """
    Aggregate workspace-level stats for project manager overview.

    Queries:
        - COUNT videos by status
        - SUM duration_s / 60 for processed/all videos
        - SUM size_bytes → GB
        - COUNT projects
        - Redis queue depth

    Performance note: single SQL query with conditional aggregation preferred over N+1.
    Returns: WorkspaceDashboard
    """
    # TODO: implement per contract
    pass


async def get_project_dashboard(project_id: UUID, db: AsyncSession) -> ProjectDashboard:
    """
    Per-project video inventory with counting line status flags.

    Returns: ProjectDashboard with VideoSummary list.
    """
    # TODO: implement per contract
    pass
