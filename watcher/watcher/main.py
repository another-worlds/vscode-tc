# Grand Contract v1.0 — M4 Watcher entry point
import asyncio
import logging
import time
from watchdog.observers.inotify import InotifyObserver
from watcher.folder_watcher import VideoFileHandler, ProjectIdResolver
from watcher.config import settings

logger = logging.getLogger(__name__)


def main() -> None:
    """
    Start watchdog InotifyObserver on VIDEO_DIR.

    Uses InotifyObserver explicitly (Linux only, Debian Trixie).
    Runs until SIGTERM/SIGINT.

    Side-effects:
        - Logs every detected .mp4 file
        - Calls backend API for each new file

    Error modes:
        - Exits with code 1 if VIDEO_DIR does not exist
        - Reconnects if backend is temporarily unavailable (best-effort)
    """
    logging.basicConfig(level=logging.INFO)
    resolver = ProjectIdResolver()
    handler = VideoFileHandler(settings.BACKEND_URL, resolver)
    observer = InotifyObserver()
    observer.schedule(handler, settings.VIDEO_DIR, recursive=True)
    observer.start()
    logger.info("Watching %s for new .mp4 files...", settings.VIDEO_DIR)
    try:
        while True:
            time.sleep(5)
    except (KeyboardInterrupt, SystemExit):
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
