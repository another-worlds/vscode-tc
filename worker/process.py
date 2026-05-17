# GPU Worker process - to be implemented in Task 7
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("GPU Worker starting...")
    logger.info(f"GPU Device: {os.environ.get('GPU_DEVICE', '0')}")
    logger.info(f"Config path: {os.environ.get('YOLO_CONFIG_PATH', '/app/config/yolo_config.json')}")
    
    # Load config
    config_path = os.environ.get('YOLO_CONFIG_PATH', '/app/config/yolo_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            logger.info(f"Config loaded: {config}")
    
    logger.info("Worker ready - waiting for jobs from Redis queue")
    # TODO: Implement job queue listening in Task 7
    
    while True:
        import time
        time.sleep(10)

if __name__ == "__main__":
    main()
