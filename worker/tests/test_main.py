import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker import main


@pytest.mark.asyncio
async def test_update_video_status_success(monkeypatch):
    mock_response = MagicMock()
    mock_response.is_success = True

    async def mock_patch(url, json):
        return mock_response

    mock_client = AsyncMock()
    mock_client.patch.side_effect = mock_patch
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout: mock_client)
    monkeypatch.setattr(main.asyncio, "sleep", AsyncMock())

    await main.update_video_status("vid", "proj", "PROCESSING")
    mock_client.patch.assert_called_once()


@pytest.mark.asyncio
async def test_update_video_status_retry_then_success(monkeypatch):
    responses = [MagicMock(is_success=False, status_code=500, text="err"), MagicMock(is_success=True)]

    async def mock_patch(url, json):
        return responses.pop(0)

    mock_client = AsyncMock()
    mock_client.patch.side_effect = mock_patch
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout: mock_client)
    monkeypatch.setattr(main.asyncio, "sleep", AsyncMock())

    await main.update_video_status("vid", "proj", "PROCESSING")
    assert mock_client.patch.call_count == 2


@pytest.mark.asyncio
async def test_update_video_status_logs_failure(monkeypatch):
    async def mock_patch(url, json):
        raise main.httpx.RequestError("fail")

    mock_client = AsyncMock()
    mock_client.patch.side_effect = mock_patch
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout: mock_client)
    monkeypatch.setattr(main.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(main.logger, "error", MagicMock())

    await main.update_video_status("vid", "proj", "ERROR")
    assert mock_client.patch.call_count == 3
    main.logger.error.assert_called_once()
