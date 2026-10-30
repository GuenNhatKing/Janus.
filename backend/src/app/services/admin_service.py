"""Nghiệp vụ quản trị người dùng."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import ForbiddenError, NotFoundError
from app.models import User, UserRole


def list_users(db: Session, search: str | None = None) -> list[User]:
    query = select(User).order_by(User.created_at.desc())
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(User.display_name.ilike(pattern) | User.email.ilike(pattern))
    return list(db.scalars(query))


def get_user(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Không tìm thấy người dùng")
    return user


def list_moderators(db: Session) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(User.role.in_((UserRole.moderator, UserRole.admin)))
            .order_by(User.created_at.desc())
        )
    )


def update_user_status(db: Session, user_id: UUID, actor: User, is_active: bool) -> User:
    target = get_user(db, user_id)
    if target.id == actor.id and not is_active:
        raise ForbiddenError("Không thể tự khóa tài khoản admin hiện tại")
    target.is_active = is_active
    db.commit()
    db.refresh(target)
    return target


def update_user_role(db: Session, user_id: UUID, actor: User, role: UserRole) -> User:
    target = get_user(db, user_id)
    if target.id == actor.id and role != UserRole.admin:
        raise ForbiddenError("Không thể tự thu hồi quyền admin hiện tại")
    target.role = role
    db.commit()
    db.refresh(target)
    return target
