from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Short Video Moderation API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://pbl6_app:CHANGE_ME@localhost:5432/pbl6"
    secret_key: str = "change-this-development-secret-key-32"
    access_token_expire_minutes: int = 30
    upload_dir: str = "storage/uploads"
    max_upload_size_bytes: int = 50 * 1024 * 1024
    allowed_video_extension: str = ".mp4"
    low_confidence_threshold: float = 0.4
    high_confidence_threshold: float = 0.8

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_database_url() -> str:
    url = get_settings().database_url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url
