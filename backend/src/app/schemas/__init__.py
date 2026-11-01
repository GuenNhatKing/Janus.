from app.schemas.admin import (
    AdminRoleUpdate,
    AdminUserDetail,
    AdminUserStatusUpdate,
    AdminUserSummary,
)
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.moderation import ModerationDecisionRequest
from app.schemas.report import ReportCreate, ReportResponse
from app.schemas.social import (
    BookmarkedVideosResponse,
    BookmarkResponse,
    CommentCreate,
    CommentResponse,
    CommentsResponse,
    FollowResponse,
    LikeResponse,
    UsersResponse,
)
from app.schemas.user import (
    ChangePasswordRequest,
    MessageResponse,
    ProfileUpdate,
    PublicUserResponse,
    UserCreate,
    UserResponse,
)
from app.schemas.video import (
    AIResultResponse,
    ConfirmLabelsRequest,
    FeedItem,
    FeedResponse,
    LabelResponse,
    VideoLabelsResponse,
    VideoResponse,
    VideoUpdate,
)

__all__ = [
    "AIResultResponse",
    "AdminRoleUpdate",
    "AdminUserDetail",
    "AdminUserStatusUpdate",
    "AdminUserSummary",
    "BookmarkResponse",
    "BookmarkedVideosResponse",
    "ChangePasswordRequest",
    "CommentCreate",
    "CommentResponse",
    "CommentsResponse",
    "ConfirmLabelsRequest",
    "FeedItem",
    "FeedResponse",
    "FollowResponse",
    "LabelResponse",
    "LikeResponse",
    "LoginRequest",
    "MessageResponse",
    "ModerationDecisionRequest",
    "ProfileUpdate",
    "PublicUserResponse",
    "ReportCreate",
    "ReportResponse",
    "TokenResponse",
    "UserCreate",
    "UserResponse",
    "UsersResponse",
    "VideoLabelsResponse",
    "VideoResponse",
    "VideoUpdate",
]
