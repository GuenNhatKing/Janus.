from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.user import PublicUserResponse
from app.schemas.video import VideoResponse


class LikeResponse(BaseModel):
    is_liked: bool
    like_count: int


class BookmarkResponse(BaseModel):
    is_bookmarked: bool


class PageInfo(BaseModel):
    page: int
    page_size: int
    total: int


class BookmarkedVideosResponse(PageInfo):
    items: list[VideoResponse]


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Nội dung bình luận không được để trống")
        return value


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    video_id: UUID
    content: str | None
    is_deleted: bool
    created_at: datetime
    author: PublicUserResponse


class CommentsResponse(PageInfo):
    items: list[CommentResponse]


class FollowResponse(BaseModel):
    is_following: bool


class UsersResponse(PageInfo):
    items: list[PublicUserResponse]
