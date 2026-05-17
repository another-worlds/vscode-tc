# Grand Contract v1.0 — M10 Export Service
from __future__ import annotations
from uuid import UUID
from io import BytesIO
import openpyxl
from sqlalchemy.ext.asyncio import AsyncSession


async def export_counting_results_xlsx(video_id: UUID, db: AsyncSession) -> BytesIO:
    """
    Generate an Excel workbook with counting results for all lines in a video.

    Sheet structure:
        Sheet "Summary":
            Row 1: Video filename, resolution, duration
            Row 3+: Line Name | Count In | Count Out | Total | Car% | Truck% | Moto% | ...

        Sheet "Trajectories" (optional summary):
            Total unique track IDs, per-class breakdown

    Args:
        video_id: must reference a PROCESSED video with counting results

    Returns:
        BytesIO containing the .xlsx file contents (seeked to 0).

    Side-effects: fires audit log RESULTS_DOWNLOADED.

    Error modes:
        - HTTPException 404 if video not found
        - HTTPException 422 if no counting results exist yet
    """
    # TODO: implement per contract
    pass
