from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Short Video Moderation API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://pbl6_app:CHANGE_ME@localhost:5432/pbl6"
    secret_key: str = "change-this-development-secret-key-32"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_reset_expire_minutes: int = 30
    upload_dir: str = "storage/uploads"
    storage_driver: str = "local"
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket_name: str = ""
    s3_public_domain: str = ""
    s3_region: str = "auto"
    s3_presigned_url_expire_seconds: int = 900
    max_upload_size_bytes: int = 50 * 1024 * 1024
    allowed_video_extension: str = ".mp4"
    low_confidence_threshold: float = 0.4
    high_confidence_threshold: float = 0.8
    # Các origin được phép gọi API từ trình duyệt, phân tách bằng dấu phẩy.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Tích hợp NSFW-Detection (pipeline Adult) ---
    # auto   : chạy NSFW-Detection; nếu môi trường AI chưa sẵn sàng thì dùng kết quả mock.
    # required: bắt buộc chạy NSFW-Detection; không chạy được thì job chuyển sang failed.
    # off    : tắt, luôn dùng kết quả mock như trước đây.
    ai_analysis_mode: str = "auto"
    # Thư mục NSFW-Detection/src (tương đối so với backend/); để trống sẽ dùng
    # backend/NSFW-Detection/src.
    nsfw_pipeline_dir: str = ""
    # Interpreter dùng để chạy pipeline; để trống sẽ dùng interpreter của backend.
    nsfw_python: str = ""
    nsfw_timeout_seconds: int = 600

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_storage_config(self) -> None:
        driver = self.storage_driver.strip().lower()
        if driver not in {"local", "s3"}:
            raise ValueError(f"STORAGE_DRIVER không hợp lệ: {self.storage_driver!r}")
        if driver == "s3":
            required = {
                "S3_ENDPOINT_URL": self.s3_endpoint_url,
                "S3_ACCESS_KEY_ID": self.s3_access_key_id,
                "S3_SECRET_ACCESS_KEY": self.s3_secret_access_key,
                "S3_BUCKET_NAME": self.s3_bucket_name,
            }
            missing = [name for name, value in required.items() if not value.strip()]
            if missing:
                raise ValueError(
                    "Thiếu cấu hình bắt buộc cho STORAGE_DRIVER=s3: "
                    + ", ".join(missing)
                )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_database_url() -> str:
    url = get_settings().database_url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url
