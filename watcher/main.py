# Yandex Disk Watcher service - to be implemented in Task 6
import os
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            logger.info(f"File created: {event.src_path}")
            # TODO: Implement ingestion logic in Task 6

def main():
    mount_path = os.environ.get('YANDEX_MOUNT_PATH', '/mnt/yandex')
    logger.info(f"Starting Yandex Disk watcher at {mount_path}")
    
    if not os.path.exists(mount_path):
        logger.warning(f"Mount path does not exist: {mount_path}")
        logger.info("Waiting for mount path to become available...")
    
    event_handler = VideoEventHandler()
    observer = Observer()
    observer.schedule(event_handler, path=mount_path, recursive=True)
    
    logger.info("Watcher ready")
    observer.start()
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    main()
