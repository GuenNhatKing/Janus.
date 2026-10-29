from fastapi import APIRouter, Depends

from app.dependencies import current_user
from app.models import User
from app.schemas import UserResponse

router = APIRouter(tags=["users"])


@router.get("/profile", response_model=UserResponse)
def profile(user: User = Depends(current_user)) -> User:
    return user
