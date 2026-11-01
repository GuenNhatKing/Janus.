"""Nghiệp vụ tài khoản: đăng ký và xác thực."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.exceptions import ConflictError, UnauthorizedError
from app.models import User
from app.schemas import LoginRequest, UserCreate
from app.services.profile_service import allocate_discriminator


def create_user(db: Session, payload: UserCreate) -> User:
    """Tạo người dùng mới; email đã tồn tại là xung đột nghiệp vụ (409)."""
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise ConflictError("Email đã được sử dụng")
    for _ in range(5):
        user = User(
            email=email,
            display_name=payload.display_name,
            discriminator=allocate_discriminator(db, payload.display_name),
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            if db.scalar(select(User).where(User.email == email)):
                raise ConflictError("Email đã được sử dụng") from None
        else:
            db.refresh(user)
            return user
    raise ConflictError("Không thể cấp mã định danh, vui lòng thử lại")


def authenticate(db: Session, payload: LoginRequest) -> User:
    """Xác thực bằng email + mật khẩu; sai thông tin là 401."""
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Email hoặc mật khẩu không chính xác")
    return user
