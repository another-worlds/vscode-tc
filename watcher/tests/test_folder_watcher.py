from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

import pytest

from watcher.folder_watcher import VideoFileHandler, ProjectIdResolver
from watcher import config


class DummyEvent:
    def __init__(self, path, is_directory=False, dest_path=None):
        self.src_path = path
        self.dest_path = dest_path or path
        self.is_directory = is_directory


class DummyAsyncClient:
    def __init__(self, timeout):
        self.timeout = timeout
        self.post = AsyncMock(return_value=MagicMock(status_code=200, text="ok"))

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.parametrize("filepath", ["/data/videos/test.mp4", "/data/videos/sub/test.MP4"])
def test_handle_new_file_posts_to_backend(monkeypatch, filepath):
    instances = []

    class DummyAsyncClientCapture(DummyAsyncClient):
        def __init__(self, timeout):
            super().__init__(timeout)
            instances.append(self)

    monkeypatch.setattr("watcher.folder_watcher.httpx.AsyncClient", DummyAsyncClientCapture)
    monkeypatch.setattr(config.settings, "DEFAULT_PROJECT_ID", "00000000-0000-0000-0000-000000000000")

    handler = VideoFileHandler("http://backend:8000", ProjectIdResolver())
    handler._handle_new_file(filepath)

    assert len(instances) == 1
    assert instances[0].post.await_count == 1


def test_project_id_resolver_uses_default_project_id(monkeypatch):
    monkeypatch.setattr(config.settings, "DEFAULT_PROJECT_ID", "11111111-1111-1111-1111-111111111111")
    resolver = ProjectIdResolver()
    assert resolver.resolve("/data/videos/test.mp4") == "11111111-1111-1111-1111-111111111111"
