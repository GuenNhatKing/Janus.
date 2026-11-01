"""Ứng dụng FastAPI: khởi tạo, middleware, xử lý lỗi và đăng ký router."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.exceptions import ServiceError
from app.services.storage_service import StorageService


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.validate_storage_config()
    # Tạo thư mục upload trước request đầu tiên (thay cho on_event("startup") đã deprecated).
    if settings.storage_driver.strip().lower() == "local":
        Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    else:
        StorageService()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    # CORS giới hạn theo cấu hình; không mở cho mọi origin.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(ServiceError)
    async def handle_service_error(_: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(api_router)
    return application


app = create_app()
