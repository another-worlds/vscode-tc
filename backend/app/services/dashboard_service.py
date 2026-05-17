# Grand Contract v1.0 — M9 Dashboard Service
from __future__ import annotations
from uuid import UUID
from sqlalchemy import select, func, case, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.dashboard import WorkspaceDashboard, ProjectDashboard, VideoSummary
from app.services.queue_service import get_queue_depth
from app.models.project import Project
from app.models.video import Video, VideoStatus
from app.models.counting_line import CountingLine, CountingResult


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
    stats_stmt = (
        select(
            func.count(Video.id).label("total_videos"),
            func.sum(case((Video.status == VideoStatus.PROCESSED, 1), else_=0)).label("processed_videos"),
            func.sum(case((Video.status == VideoStatus.PENDING, 1), else_=0)).label("pending_videos"),
            func.coalesce(func.sum(Video.duration_s), 0.0).label("total_duration_s"),
            func.coalesce(func.sum(case((Video.status == VideoStatus.PROCESSED, Video.duration_s), else_=0.0)), 0.0).label("processed_duration_s"),
            func.coalesce(func.sum(Video.size_bytes), 0).label("storage_used_bytes"),
            func.count(distinct(Project.id)).label("total_projects"),
        )
        .select_from(Project)
        .join(Video, Video.project_id == Project.id, isouter=True)
        .where(Project.workspace_id == workspace_id)
    )

    active_projects_stmt = (
        select(func.count(distinct(Video.project_id)))
        .select_from(Project)
        .join(Video, Video.project_id == Project.id)
        .where(Project.workspace_id == workspace_id, Video.status != VideoStatus.PROCESSED)
    )

    stats_result = await db.execute(stats_stmt)
    row = stats_result.one()
    active_projects = await db.scalar(active_projects_stmt)
    queue_depth = await get_queue_depth()

    return WorkspaceDashboard(
        workspace_id=workspace_id,
        total_videos=int(row.total_videos or 0),
        processed_videos=int(row.processed_videos or 0),
        pending_videos=int(row.pending_videos or 0),
        total_duration_min=float((row.total_duration_s or 0.0) / 60.0),
        processed_duration_min=float((row.processed_duration_s or 0.0) / 60.0),
        storage_used_gb=float((row.storage_used_bytes or 0) / (1024 ** 3)),
        total_projects=int(row.total_projects or 0),
        active_projects=int(active_projects or 0),
        queue_depth=int(queue_depth or 0),
    )


async def get_project_dashboard(project_id: UUID, db: AsyncSession) -> ProjectDashboard:
    """
    Per-project video inventory with counting line status flags.

    Returns: ProjectDashboard with VideoSummary list.
    """
    stmt = (
        select(
            Video.id,
            Video.filename,
            Video.resolution_w,
            Video.resolution_h,
            Video.size_bytes,
            Video.duration_s,
            Video.status,
            func.count(distinct(CountingLine.id)).label("line_count"),
            func.count(distinct(CountingResult.id)).label("result_count"),
        )
        .select_from(Video)
        .outerjoin(CountingLine, CountingLine.video_id == Video.id)
        .outerjoin(CountingResult, CountingResult.counting_line_id == CountingLine.id)
        .where(Video.project_id == project_id)
        .group_by(Video.id)
    )

    result = await db.execute(stmt)
    videos = []
    for row in result.fetchall():
        resolution = None
        if row.resolution_w is not None and row.resolution_h is not None:
            resolution = f"{row.resolution_w}x{row.resolution_h}"

        duration_min = None
        if row.duration_s is not None:
            duration_min = float(row.duration_s / 60.0)

        videos.append(
            VideoSummary(
                id=row.id,
                filename=row.filename,
                resolution=resolution,
                size_bytes=row.size_bytes,
                duration_min=duration_min,
                status=row.status.value if hasattr(row.status, "value") else str(row.status),
                has_counting_lines=(row.line_count or 0) > 0,
                has_results=(row.result_count or 0) > 0,
            )
        )

    return ProjectDashboard(project_id=project_id, videos=videos)
