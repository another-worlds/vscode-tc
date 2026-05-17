# Grand Contract v1.0 — M6 GPU Worker: Worker config
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://tc_user:changeme@db:5432/trafficcounting"
    REDIS_URL: str = "redis://redis:6379/0"
    VIDEO_DIR: str = "/data/videos"
    FRAME_DIR: str = "/data/frames"
    PARQUET_DIR: str = "/data/parquet"
    YOLO_MODEL_KEY: str = "yolov8m"
    FRAMES_SAMPLE_COUNT: int = 100
    BACKEND_URL: str = "http://backend:8000"
    DETECTOR_CONF: float = 0.25
    DETECTOR_IOU: float = 0.45
    DETECTOR_IMGSZ: int = 640
    TRACKER_MAX_AGE: int = 30


settings = WorkerSettings()
