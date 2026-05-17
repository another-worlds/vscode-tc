from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.routers.internal_videos import register_video_internal
from app.schemas.video import VideoOut


@pytest.mark.asyncio
async def test_register_video_internal_missing_fields():
    with pytest.raises(HTTPException) as exc_info:
        await register_video_internal({}, db=AsyncMock())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_register_video_internal_invalid_uuid():
    payload = {"filepath": "/data/videos/test.mp4", "project_id": "not-a-uuid"}
    with pytest.raises(HTTPException) as exc_info:
        await register_video_internal(payload, db=AsyncMock())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_register_video_internal_success(monkeypatch):
    payload = {"filepath": "/data/videos/test.mp4", "project_id": str(uuid4()), "source": "watcher"}
    video = MagicMock()
    video.id = uuid4()
    video.filepath = payload["filepath"]
    video.filename = "test.mp4"
    video.project_id = uuid4()
    video.resolution_w = None
    video.resolution_h = None
    video.duration_s = None
    video.size_bytes = None
    video.fps = None
    video.status = None
    video.error_message = None
    video.uploaded_at = None
    video.uploaded_by = None
    video.processing_started_at = None
    video.processed_at = None
    video.frame_count = None
    video.parquet_path = None

    register_mock = AsyncMock(return_value=video)
    enqueue_mock = AsyncMock()
    monkeypatch.setattr("app.routers.internal_videos.video_service.register_video_from_path", register_mock)
    monkeypatch.setattr("app.routers.internal_videos.queue_service.enqueue_video", enqueue_mock)

    result = await register_video_internal(payload, db=AsyncMock())

    register_mock.assert_awaited_once()
    enqueue_mock.assert_awaited_once_with(video.id, video.filepath, payload["project_id"])
    assert isinstance(result, VideoOut)
