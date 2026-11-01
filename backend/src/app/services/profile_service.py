"""Nghiệp vụ profile, discriminator và đổi mật khẩu."""

import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.exceptions import ConflictError, InvalidInputError
from app.models import User
from app.schemas import ChangePasswordRequest, ProfileUpdate

MAX_DISCRIMINATOR = 9999
DISCRIMINATOR_RETRIES = 20


def allocate_discriminator(
    db: Session, display_name: str, preferred: str | None = None
) -> str:
    """Return an unused four-digit discriminator for a display name."""
    if preferred and not db.scalar(
        select(User.id).where(
            User.display_name == display_name,
            User.discriminator == preferred,
        )
    ):
        return preferred
    for _ in range(DISCRIMINATOR_RETRIES):
        candidate = f"{secrets.randbelow(MAX_DISCRIMINATOR) + 1:04d}"
        if not db.scalar(
            select(User.id).where(
                User.display_name == display_name,
                User.discriminator == candidate,
            )
        ):
            return candidate
    raise ConflictError("Không thể cấp mã định danh, vui lòng thử lại")


def update_profile(db: Session, user: User, payload: ProfileUpdate) -> User:
    values = payload.model_dump(exclude_unset=True)
    for _ in range(DISCRIMINATOR_RETRIES):
        current = db.get(User, user.id)
        if current is None:
            raise ConflictError("Tài khoản không còn tồn tại")
        if "display_name" in values and values["display_name"] != current.display_name:
            current.discriminator = allocate_discriminator(
                db, values["display_name"], preferred=current.discriminator
            )
            current.display_name = values["display_name"]
        if "bio" in values:
            current.bio = values["bio"]
        if "avatar_url" in values:
            current.avatar_url = (
                str(values["avatar_url"]) if values["avatar_url"] else None
            )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            db.refresh(current)
            return current
    raise ConflictError("Tên hiển thị đã xảy ra xung đột, vui lòng thử lại")


def change_password(
    db: Session, user: User, payload: ChangePasswordRequest
) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise InvalidInputError("Mật khẩu hiện tại không chính xác")
    if verify_password(payload.new_password, user.password_hash):
        raise InvalidInputError("Mật khẩu mới không được trùng mật khẩu cũ")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
