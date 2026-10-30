from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, moderation, users, videos

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(videos.router)
api_router.include_router(moderation.router)
api_router.include_router(admin.router)
