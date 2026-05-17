# Grand Contract v1.0 — Watcher config
from pydantic_settings import BaseSettings, SettingsConfigDict


class WatcherSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    VIDEO_DIR: str = "/data/videos"
    BACKEND_URL: str = "http://backend:8000"
    DEFAULT_PROJECT_ID: str = ""
    DEFAULT_WORKSPACE_ID: str = ""


settings = WatcherSettings()
