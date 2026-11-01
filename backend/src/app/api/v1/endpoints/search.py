from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import PublicUserResponse, SearchTagResponse, VideoResponse
from app.services import search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/videos-by-tag/grid", response_model=SearchTagResponse)
def videos_by_tag_grid(
    tag: str = Query(..., min_length=1),
    limit: int = Query(default=12, ge=1, le=20),
    cursor: datetime | None = Query(default=None),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> SearchTagResponse:
    return search_service.search_published_videos_by_tag(
        db, tag, limit=limit, cursor=cursor
    )


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
