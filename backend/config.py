# Backend configuration and settings
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application configuration from environment variables"""
    
    # Database
    db_url: str = os.environ.get(
        "DB_URL",
        "postgresql://tc_user:tc_password@postgres:5432/traffic_count"
    )
    
    # JWT / Security
    secret_key: str = os.environ.get("SECRET_KEY", "your-secret-key-change-in-prod")
    algorithm: str = os.environ.get("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(
        os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    
    # Redis
    redis_url: str = os.environ.get("REDIS_URL", "redis://redis:6379")
    
    # Server
    debug: bool = os.environ.get("DEBUG", "0") == "1"
    
    # Paths
    yandex_mount_path: str = os.environ.get("YANDEX_MOUNT_PATH", "/mnt/yandex")
    parquet_store_path: str = "/app/parquet_store"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
