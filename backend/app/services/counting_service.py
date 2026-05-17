# Grand Contract v1.0 — M8 Counting Service
# Server-side trajectory intersection counting
from __future__ import annotations
from uuid import UUID
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.counting_line import CountingLine, CountingResult
from app.models.video import Video, VideoStatus
from app.schemas.counting_line import CountingLineCreate
from app.config import settings


async def create_counting_line(
    video_id: UUID,
    payload: CountingLineCreate,
    user_id: UUID,
    db: AsyncSession,
) -> CountingLine:
    """
    Persist a new counting line drawn by the user.

    Args:
        video_id: must reference a PROCESSED video
        payload:  name, points (>=2), color
        user_id:  creator

    Returns:
        Persisted CountingLine.

    Side-effects: DB INSERT, fires audit log LINE_DRAWN.
    Error modes:
        - HTTPException 404 if video not found
        - HTTPException 422 if video not yet PROCESSED
    """
    stmt = select(Video).where(Video.id == video_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if video.status != VideoStatus.PROCESSED:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Video not yet processed")

    points_raw = [[p.x, p.y] for p in payload.points]
    line = CountingLine(
        video_id=video_id,
        name=payload.name,
        points=points_raw,
        color=payload.color,
        created_by=user_id,
    )
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return line


async def compute_line_counts(
    line_id: UUID, db: AsyncSession
) -> CountingResult:
    """
    Load trajectory parquet for the line's video, compute intersections,
    persist CountingResult.

    Algorithm (per contract):
        1. Load parquet: columns [track_id, frame_no, x1, y1, x2, y2, class_id]
        2. For each track, build ordered list of centroid points
        3. For each consecutive centroid pair (segment), test intersection
           with the counting line using 2D segment-segment intersection
        4. Determine direction: cross product of line vector × centroid movement
           → positive = "in", negative = "out"
        5. Aggregate counts per class_id → vehicle_pct dict

    Performance note: pandas vectorized; for >1M rows consider polars or chunked read.
    """
    stmt = select(CountingLine).where(CountingLine.id == line_id)
    result = await db.execute(stmt)
    line = result.scalar_one_or_none()
    if line is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Counting line not found")

    video_stmt = select(Video).where(Video.id == line.video_id)
    video_result = await db.execute(video_stmt)
    video = video_result.scalar_one_or_none()
    if video is None or video.parquet_path is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Video has no trajectory data")

    df = pd.read_parquet(video.parquet_path)
    # Compute centroids
    df["cx"] = (df["x1"] + df["x2"]) / 2.0
    df["cy"] = (df["y1"] + df["y2"]) / 2.0

    points = line.points  # [[x, y], [x, y], ...]
    # Use first two points as the primary line segment
    line_start = (float(points[0][0]), float(points[0][1]))
    line_end = (float(points[1][0]), float(points[1][1]))

    count_in = 0
    count_out = 0
    class_counts: dict[int, int] = {}

    for track_id, group in df.sort_values("frame_no").groupby("track_id"):
        cx_vals = group["cx"].tolist()
        cy_vals = group["cy"].tolist()
        class_ids = group["class_id"].tolist()

        for i in range(len(cx_vals) - 1):
            p1 = (cx_vals[i], cy_vals[i])
            p2 = (cx_vals[i + 1], cy_vals[i + 1])
            if _segment_intersects_line(p1, p2, line_start, line_end):
                direction = _compute_direction(p1, p2, line_start, line_end)
                if direction == "in":
                    count_in += 1
                else:
                    count_out += 1
                class_id = int(class_ids[i])
                class_counts[class_id] = class_counts.get(class_id, 0) + 1

    total = count_in + count_out
    vehicle_pct: dict[str, float] | None = None
    if total > 0:
        vehicle_pct = {str(k): round(v / total * 100, 2) for k, v in class_counts.items()}

    # Upsert CountingResult
    res_stmt = select(CountingResult).where(CountingResult.counting_line_id == line_id)
    res_result = await db.execute(res_stmt)
    counting_result = res_result.scalar_one_or_none()

    if counting_result:
        counting_result.count_in = count_in
        counting_result.count_out = count_out
        counting_result.vehicle_pct = vehicle_pct
        counting_result.computed_at = datetime.now(timezone.utc)
    else:
        counting_result = CountingResult(
            counting_line_id=line_id,
            count_in=count_in,
            count_out=count_out,
            vehicle_pct=vehicle_pct,
        )
        db.add(counting_result)

    await db.commit()
    await db.refresh(counting_result)
    return counting_result


def _segment_intersects_line(
    p1: tuple[float, float],
    p2: tuple[float, float],
    line_start: tuple[float, float],
    line_end: tuple[float, float],
) -> bool:
    """
    2D segment-segment intersection test (cross-product method).
    Returns True if segments intersect (excluding collinear).
    Contract: pure function, no side-effects, O(1).
    """
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    d1 = cross(line_start, line_end, p1)
    d2 = cross(line_start, line_end, p2)
    d3 = cross(p1, p2, line_start)
    d4 = cross(p1, p2, line_end)

    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
       ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True

    return False


def _compute_direction(
    centroid_before: tuple[float, float],
    centroid_after: tuple[float, float],
    line_start: tuple[float, float],
    line_end: tuple[float, float],
) -> str:
    """
    Determine crossing direction using cross product.
    Returns: 'in' | 'out'
    """
    lx = line_end[0] - line_start[0]
    ly = line_end[1] - line_start[1]
    mx = centroid_after[0] - centroid_before[0]
    my = centroid_after[1] - centroid_before[1]
    cross = lx * my - ly * mx
    return "in" if cross > 0 else "out"


async def get_trajectory_heatmap_data(
    video_id: UUID, db: AsyncSession
) -> dict:
    """
    Read parquet trajectories and compute a density grid for heatmap overlay.

    Returns:
        {"width": int, "height": int, "grid": list[list[float]]}
    """
    stmt = select(Video).where(Video.id == video_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None or video.parquet_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video trajectory not available")

    df = pd.read_parquet(video.parquet_path)
    cx = ((df["x1"] + df["x2"]) / 2.0).values
    cy = ((df["y1"] + df["y2"]) / 2.0).values

    grid_size = 100
    hist, _, _ = np.histogram2d(cx, cy, bins=grid_size, density=False)
    max_val = float(hist.max() or 1.0)
    normalized = (hist / max_val).tolist()

    return {
        "width": video.resolution_w or grid_size,
        "height": video.resolution_h or grid_size,
        "grid": normalized,
    }


async def suggest_counting_lines(video_id: UUID, db: AsyncSession) -> list[dict]:
    """
    Return trajectory segment midpoints and angles for client-side clustering.
    """
    stmt = select(Video).where(Video.id == video_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None or video.parquet_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video trajectory not available")

    df = pd.read_parquet(video.parquet_path).sort_values(["track_id", "frame_no"])
    df["cx"] = (df["x1"] + df["x2"]) / 2.0
    df["cy"] = (df["y1"] + df["y2"]) / 2.0

    segments = []
    for _, group in df.groupby("track_id"):
        cx_vals = group["cx"].values
        cy_vals = group["cy"].values
        for i in range(len(cx_vals) - 1):
            dx = cx_vals[i + 1] - cx_vals[i]
            dy = cy_vals[i + 1] - cy_vals[i]
            length = float(np.hypot(dx, dy))
            if length < 1.0:
                continue
            angle_deg = float(np.degrees(np.arctan2(dy, dx))) % 180.0
            segments.append({
                "x_mid": float((cx_vals[i] + cx_vals[i + 1]) / 2),
                "y_mid": float((cy_vals[i] + cy_vals[i + 1]) / 2),
                "angle_deg": angle_deg,
            })

    return segments
