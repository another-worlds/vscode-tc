# Grand Contract v1.0 — M1 Auth / App configuration
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl, field_validator
from typing import Literal


class Settings(BaseSettings):
    """
    Single source of truth for all runtime configuration.
    Populated from environment variables / .env file.

    Invariants:
        - SECRET_KEY must be >= 32 chars in non-DEBUG mode
        - OAUTH_PROVIDER must be 'google' or 'yandex'
        - DEBUG=1 disables OAuth and grants ADMIN to all requests
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    DEBUG: int = 1
    SECRET_KEY: str = "dev_secret_change_me"

    # OAuth2
    OAUTH_PROVIDER: Literal["google", "yandex"] = "google"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    YANDEX_CLIENT_ID: str = ""
    YANDEX_CLIENT_SECRET: str = ""
    OAUTH_REDIRECT_URI: str = "http://localhost/api/auth/callback"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://tc_user:changeme@db:5432/trafficcounting"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Storage
    VIDEO_DIR: str = "/data/videos"
    FRAME_DIR: str = "/data/frames"
    PARQUET_DIR: str = "/data/parquet"

    # Worker
    YOLO_MODEL_KEY: str = "yolov8m"
    FRAMES_SAMPLE_COUNT: int = 100

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """
        Invariant: SECRET_KEY >= 32 chars when DEBUG=0.
        Side-effect: none.
        Error mode: raises ValueError if violated in production.
        """
        # Allow short key only in DEBUG mode
        debug_val = info.data.get("DEBUG", 1)
        if debug_val == 0 and len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production (DEBUG=0)")
        return v


settings = Settings()
