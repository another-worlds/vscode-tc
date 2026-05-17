from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.video_service import probe_video_metadata, upload_video_ui


@pytest.mark.asyncio
async def test_probe_video_metadata_missing_file_returns_empty():
    metadata = await probe_video_metadata("/tmp/nonexistent-file-12345.mp4")
    assert metadata == {}


@pytest.mark.asyncio
async def test_upload_video_ui_rejects_non_mp4():
    file_bytes = b"test"
    filename = "video.mov"
    project_id = uuid4()
    uploaded_by = uuid4()
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await upload_video_ui(file_bytes, filename, project_id, uploaded_by, db)

    assert exc_info.value.status_code == 400
    assert "Only .mp4 uploads are supported" in str(exc_info.value.detail)
