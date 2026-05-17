# Grand Contract v1.0 — M4 Folder Watcher
"""
Monitors VIDEO_DIR for new .mp4 files using watchdog inotify (Linux).

On NEW FILE (closed/moved-in event):
    1. POST to backend /internal/videos/register {filepath, source="watcher"}
    2. Backend creates Video record (status=PENDING) + enqueues job

Invariant: duplicate paths are idempotent (backend deduplicates by filepath).
Invariant: only .mp4 extensions processed.
"""
from __future__ import annotations
import asyncio
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileClosedEvent, FileMovedEvent
import httpx
from watcher.config import settings

logger = logging.getLogger(__name__)


class VideoFileHandler(FileSystemEventHandler):
    """
    Watchdog event handler for new MP4 files.

    Fires on:
        - FileClosedEvent (Linux inotify IN_CLOSE_WRITE): file written fully
        - FileMovedEvent: file moved/renamed into watch directory

    Invariant: only .mp4 files trigger registration.
    """

    def __init__(self, backend_url: str, project_id_resolver: "ProjectIdResolver"):
        """
        Args:
            backend_url:          base URL of backend API (e.g. http://backend:8000)
            project_id_resolver:  strategy for mapping filepath → project_id
                                  (default: use DEFAULT_PROJECT_ID env if set,
                                   else first project in workspace)
        """
        # TODO: implement per contract
        pass

    def on_closed(self, event: FileClosedEvent) -> None:
        """Handle file-closed-for-write (inotify IN_CLOSE_WRITE)."""
        # TODO: implement per contract
        pass

    def on_moved(self, event: FileMovedEvent) -> None:
        """Handle file moved into watch directory (e.g. ydisk sync renames temp→final)."""
        # TODO: implement per contract
        pass

    def _handle_new_file(self, filepath: str) -> None:
        """
        Validate extension, call backend register endpoint.

        Side-effects:
            - POST /internal/videos/register
            - Logs on success/failure

        Error modes: logs HTTP errors, does not retry (watcher is best-effort)
        """
        # TODO: implement per contract
        pass


class ProjectIdResolver:
    """
    Maps a filepath to a project_id for watcher-ingested videos.

    Strategy (in order):
        1. If DEFAULT_PROJECT_ID env is set → use it
        2. If filepath is under a subdirectory named by project slug → match by name
        3. Fallback: first project in DEFAULT_WORKSPACE_ID

    Extensible: subclass and override resolve() for custom mapping logic.
    """

    def resolve(self, filepath: str) -> str | None:
        """
        Args:
            filepath: absolute path to MP4

        Returns:
            project_id UUID string or None (caller should skip if None)
        """
        # TODO: implement per contract
        pass
