from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import current_user
from app.models import User
from app.schemas import (
    ChangePasswordRequest,
    MessageResponse,
    ProfileUpdate,
    UserResponse,
)
from app.services import profile_service

router = APIRouter(tags=["users"])


@router.get("/profile", response_model=UserResponse)
def profile(user: User = Depends(current_user)) -> User:  # noqa: B008
    return user


@router.patch("/profile", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> User:
    return profile_service.update_profile(db, user, payload)


@router.post(
    "/profile/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> MessageResponse:
    profile_service.change_password(db, user, payload)
    return MessageResponse(message="Đổi mật khẩu thành công")
