from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import PublicUserResponse, VideoResponse
from app.services import search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/videos-by-tag", response_model=list[VideoResponse])
def videos_by_tag(
    tag: str = Query(..., min_length=1),
    db: Session = Depends(get_db),  # noqa: B008
):
    return search_service.search_videos_by_tag(db, tag)


@router.get("/users", response_model=list[PublicUserResponse])
def users(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),  # noqa: B008
):
    return search_service.search_users(db, q)
