from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import require_roles
from app.models import Report, User, UserRole, Video
from app.schemas import ModerationDecisionRequest, ReportResponse, VideoResponse
from app.services import moderation_service

router = APIRouter(prefix="/moderation", tags=["moderation"])


@router.get("/queue", response_model=list[VideoResponse])
def moderation_queue(
    user: User = Depends(require_roles(UserRole.moderator, UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[Video]:
    return moderation_service.moderation_queue(db)


@router.post("/videos/{video_id}/decision", status_code=status.HTTP_204_NO_CONTENT)
def moderation_decision(
    video_id: UUID,
    payload: ModerationDecisionRequest,
    user: User = Depends(require_roles(UserRole.moderator, UserRole.admin)),
    db: Session = Depends(get_db),
) -> None:
    moderation_service.decide_video(db, video_id, user, payload.action, payload.reason)


@router.get("/reports", response_model=list[ReportResponse])
def moderation_reports(
    user: User = Depends(require_roles(UserRole.moderator, UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[Report]:
    return moderation_service.list_open_reports(db)


@router.post("/reports/{report_id}/decision", status_code=status.HTTP_204_NO_CONTENT)
def report_decision(
    report_id: UUID,
    payload: ModerationDecisionRequest,
    user: User = Depends(require_roles(UserRole.moderator, UserRole.admin)),
    db: Session = Depends(get_db),
) -> None:
    moderation_service.decide_report(db, report_id, user, payload.action, payload.reason)
