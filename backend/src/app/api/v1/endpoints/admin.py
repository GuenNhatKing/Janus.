from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import require_roles
from app.models import User, UserRole
from app.schemas import AdminRoleUpdate, AdminUserDetail, AdminUserStatusUpdate, AdminUserSummary
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserSummary])
def admin_list_users(
    search: str | None = None,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[User]:
    return admin_service.list_users(db, search)


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def admin_get_user(
    user_id: UUID,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> User:
    return admin_service.get_user(db, user_id)


@router.patch("/users/{user_id}/status", response_model=AdminUserDetail)
def admin_update_user_status(
    user_id: UUID,
    payload: AdminUserStatusUpdate,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> User:
    return admin_service.update_user_status(db, user_id, user, payload.is_active)


@router.get("/moderators", response_model=list[AdminUserSummary])
def admin_list_moderators(
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[User]:
    return admin_service.list_moderators(db)


@router.patch("/users/{user_id}/role", response_model=AdminUserDetail)
def admin_update_user_role(
    user_id: UUID,
    payload: AdminRoleUpdate,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> User:
    return admin_service.update_user_role(db, user_id, user, payload.role)
