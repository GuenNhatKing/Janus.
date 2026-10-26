import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Base, engine, get_db
from app.dependencies import access_payload, current_user, require_roles
from app.models import (
    AIJob,
    Appeal,
    AppealStatus,
    JobStatus,
    Label,
    ModerationAction,
    ModerationReview,
    PasswordResetToken,
    RefreshToken,
    Report,
    ReportStatus,
    RevokedToken,
    User,
    UserRole,
    Video,
    VideoLabel,
    VideoStatus,
)
from app.schemas import (
    AIResultResponse,
    AdminLabelCreate,
    AdminLabelResponse,
    AdminLabelUpdate,
    AdminRoleUpdate,
    AdminUserDetail,
    AdminUserStatusUpdate,
    AdminUserSummary,
    AdminVideoStatusUpdate,
    AppealCreate,
    AppealDecisionRequest,
    AppealResponse,
    LabelsUpdateRequest,
    LoginRequest,
    LogoutRequest,
    ModeratorStatsResponse,
    ModerationDecisionRequest,
    PasswordForgotRequest,
    PasswordForgotResponse,
    PasswordResetRequest,
    ProfileUpdate,
    RefreshRequest,
    ReportCreate,
    ReportResponse,
    SystemStatsResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
    VideoLabelInfo,
    VideoResponse,
    VideoSearchItem,
)
from app.security import create_access_token, hash_opaque_token, hash_password, new_opaque_token, verify_password
from app.services import (
    as_aware,
    confidence_level,
    issue_refresh_token,
    purge_expired_revoked_tokens,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    run_video_analysis,
    validate_mp4_content,
)

logger = logging.getLogger(__name__)
settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


@app.on_event("startup")
def create_storage() -> None:
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=409, detail="Email đã được sử dụng")
    user = User(email=payload.email.lower(), display_name=payload.display_name, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không chính xác")
    refresh_token = issue_refresh_token(db, user)
    db.commit()
    return TokenResponse(access_token=create_access_token(user), refresh_token=refresh_token)


@app.get("/api/v1/profile", response_model=UserResponse)
def profile(user: User = Depends(current_user)) -> User:
    return user


@app.get("/api/v1/admin/users", response_model=list[AdminUserSummary])
def admin_list_users(
    search: str | None = None,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[User]:
    query = select(User).order_by(User.created_at.desc())
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(User.display_name.ilike(pattern) | User.email.ilike(pattern))
    return list(db.scalars(query))


@app.get("/api/v1/admin/users/{user_id}", response_model=AdminUserDetail)
def admin_get_user(
    user_id: UUID,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    return target


@app.patch("/api/v1/admin/users/{user_id}/status", response_model=AdminUserDetail)
def admin_update_user_status(
    user_id: UUID,
    payload: AdminUserStatusUpdate,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    if target.id == user.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="Không thể tự khóa tài khoản admin hiện tại")
    target.is_active = payload.is_active
    db.commit()
    db.refresh(target)
    return target


@app.get("/api/v1/admin/moderators", response_model=list[AdminUserSummary])
def admin_list_moderators(
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(User.role.in_((UserRole.moderator, UserRole.admin)))
            .order_by(User.created_at.desc())
        )
    )


@app.patch("/api/v1/admin/users/{user_id}/role", response_model=AdminUserDetail)
def admin_update_user_role(
    user_id: UUID,
    payload: AdminRoleUpdate,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    if target.id == user.id and payload.role != UserRole.admin:
        raise HTTPException(status_code=400, detail="Không thể tự thu hồi quyền admin hiện tại")
    target.role = payload.role
    db.commit()
    db.refresh(target)
    return target


@app.post("/api/v1/videos", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    caption: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Video:
    filename = file.filename or ""
    if Path(filename).suffix.lower() != settings.allowed_video_extension or file.content_type != "video/mp4":
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận tệp MP4")
    content = file.file.read(settings.max_upload_size_bytes + 1)
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail="Video vượt quá dung lượng 50MB")
    try:
        validate_mp4_content(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    video = Video(
        owner_id=user.id,
        original_filename=Path(filename).name,
        storage_path="",
        mime_type="video/mp4",
        size_bytes=len(content),
        caption=caption,
    )
    db.add(video)
    db.flush()
    path = Path(settings.upload_dir) / f"{video.id}.mp4"
    path.write_bytes(content)
    video.storage_path = str(path)
    job = AIJob(video_id=video.id)
    db.add(job)
    db.commit()
    db.refresh(video)
    background_tasks.add_task(run_video_analysis, video.id)
    return video


@app.get("/api/v1/videos", response_model=list[VideoResponse])
def list_my_videos(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[Video]:
    return list(db.scalars(select(Video).where(Video.owner_id == user.id, Video.is_deleted.is_(False)).order_by(Video.created_at.desc())))


@app.get("/api/v1/feed", response_model=list[VideoResponse])
def feed(db: Session = Depends(get_db)) -> list[Video]:
    return list(db.scalars(select(Video).where(Video.status == VideoStatus.published, Video.is_deleted.is_(False)).order_by(Video.created_at.desc()).limit(50)))


@app.get("/api/v1/videos/{video_id}/ai", response_model=AIResultResponse)
def ai_result(video_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> AIResultResponse:
    video = db.get(Video, video_id)
    if video is None or video.is_deleted or (video.owner_id != user.id and user.role not in {UserRole.moderator, UserRole.admin}):
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    job = db.scalar(select(AIJob).where(AIJob.video_id == video_id).order_by(AIJob.created_at.desc()))
    labels = [
        {"name": item.label.name, "confidence": item.confidence, "level": item.level}
        for item in video.labels
    ]
    return AIResultResponse(video_id=video_id, job_status=job.status.value if job else "unknown", transcript=job.transcript if job else None, labels=labels)


@app.delete("/api/v1/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    video = db.get(Video, video_id)
    if video is None or video.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    video.is_deleted = True
    video.status = VideoStatus.deleted
    db.commit()


@app.post("/api/v1/videos/{video_id}/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(video_id: UUID, payload: ReportCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Report:
    video = db.get(Video, video_id)
    if video is None or video.is_deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    if db.scalar(select(Report).where(Report.video_id == video_id, Report.reporter_id == user.id, Report.status == ReportStatus.open)):
        raise HTTPException(status_code=409, detail="Bạn đã báo cáo video này")
    report = Report(video_id=video_id, reporter_id=user.id, reason=payload.reason)
    if video.status == VideoStatus.published:
        video.status = VideoStatus.pending_review
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@app.get("/api/v1/moderation/queue", response_model=list[VideoResponse])
def moderation_queue(user: User = Depends(require_roles(UserRole.moderator, UserRole.admin)), db: Session = Depends(get_db)) -> list[Video]:
    return list(db.scalars(select(Video).where(Video.status == VideoStatus.pending_review, Video.is_deleted.is_(False)).order_by(Video.created_at)))


@app.post("/api/v1/moderation/videos/{video_id}/decision", status_code=status.HTTP_204_NO_CONTENT)
def moderation_decision(
    video_id: UUID,
    payload: ModerationDecisionRequest,
    user: User = Depends(require_roles(UserRole.moderator, UserRole.admin)),
    db: Session = Depends(get_db),
) -> None:
    video = db.get(Video, video_id)
    if video is None or video.is_deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    if payload.action == ModerationAction.approve:
        video.status = VideoStatus.published
    else:
        video.status = VideoStatus.rejected
    db.add(ModerationReview(video_id=video.id, moderator_id=user.id, action=payload.action, reason=payload.reason))
    db.commit()


@app.get("/api/v1/moderation/reports", response_model=list[ReportResponse])
def moderation_reports(
    user: User = Depends(require_roles(UserRole.moderator, UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[Report]:
    return list(db.scalars(select(Report).where(Report.status == ReportStatus.open).order_by(Report.created_at)))


@app.post("/api/v1/moderation/reports/{report_id}/decision", status_code=status.HTTP_204_NO_CONTENT)
def report_decision(
    report_id: UUID,
    payload: ModerationDecisionRequest,
    user: User = Depends(require_roles(UserRole.moderator, UserRole.admin)),
    db: Session = Depends(get_db),
) -> None:
    report = db.get(Report, report_id)
    if report is None or report.status != ReportStatus.open:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo cáo đang chờ xử lý")
    video = db.get(Video, report.video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy video liên quan")
    report.status = ReportStatus.resolved if payload.action == ModerationAction.reject else ReportStatus.rejected
    if payload.action == ModerationAction.approve:
        video.status = VideoStatus.rejected
    else:
        video.status = VideoStatus.published
    db.add(ModerationReview(video_id=video.id, moderator_id=user.id, action=payload.action, reason=payload.reason))
    db.commit()


# UC001/UC002 — phiên đăng nhập, đăng xuất, làm mới token và khôi phục mật khẩu
@app.post("/api/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest | None = None,
    user: User = Depends(current_user),
    token_payload: dict = Depends(access_payload),
    db: Session = Depends(get_db),
) -> None:
    """Thu hồi access token hiện tại (jti) và refresh token nếu client gửi kèm."""
    jti = token_payload.get("jti")
    if jti and db.get(RevokedToken, jti) is None:
        expires = datetime.fromtimestamp(token_payload["exp"], tz=timezone.utc)
        db.add(RevokedToken(jti=jti, user_id=user.id, expires_at=expires))
    if payload is not None and payload.refresh_token:
        revoke_refresh_token(db, payload.refresh_token, user_id=user.id)
    purge_expired_revoked_tokens(db)
    db.commit()


@app.post("/api/v1/auth/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Đổi refresh token (đã dùng là hết hạn) lấy access token mới."""
    row = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_opaque_token(payload.refresh_token))
    )
    now = datetime.now(timezone.utc)
    if row is None or row.revoked_at is not None or as_aware(row.expires_at) <= now:
        raise HTTPException(status_code=401, detail="Refresh token không hợp lệ hoặc đã hết hạn")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Tài khoản không hợp lệ")
    row.revoked_at = now
    new_refresh = issue_refresh_token(db, user)
    db.commit()
    return TokenResponse(access_token=create_access_token(user), refresh_token=new_refresh)


@app.post(
    "/api/v1/auth/password/forgot",
    response_model=PasswordForgotResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def forgot_password(payload: PasswordForgotRequest, db: Session = Depends(get_db)) -> PasswordForgotResponse:
    """Tạo token đặt lại mật khẩu (30 phút). Chưa có kênh gửi mail nên ngoài
    môi trường production token được trả thẳng trong response để test."""
    settings = get_settings()
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    reset_token: str | None = None
    if user is not None:
        reset_token = new_opaque_token(32)
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_opaque_token(reset_token),
                expires_at=datetime.now(timezone.utc)
                + timedelta(minutes=settings.password_reset_expire_minutes),
            )
        )
        db.commit()
        logger.info(
            "Tạo token đặt lại mật khẩu cho user %s (hiệu lực %d phút)",
            user.id,
            settings.password_reset_expire_minutes,
        )
    return PasswordForgotResponse(
        detail="Nếu email tồn tại, hướng dẫn đặt lại mật khẩu đã được gửi",
        reset_token=reset_token if settings.environment != "production" else None,
    )


@app.post("/api/v1/auth/password/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: PasswordResetRequest, db: Session = Depends(get_db)) -> None:
    row = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_opaque_token(payload.token)
        )
    )
    now = datetime.now(timezone.utc)
    if row is None or row.used_at is not None or as_aware(row.expires_at) <= now:
        raise HTTPException(
            status_code=400, detail="Token đặt lại mật khẩu không hợp lệ hoặc đã hết hạn"
        )
    user = db.get(User, row.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Token đặt lại mật khẩu không hợp lệ hoặc đã hết hạn")
    user.password_hash = hash_password(payload.new_password)
    row.used_at = now
    revoke_all_refresh_tokens(db, user.id)
    db.commit()


# UC003/UC008 — hồ sơ và trải nghiệm xem video
@app.patch("/api/v1/profile", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> User:
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.new_password is not None:
        if payload.current_password is None or not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không chính xác")
        user.password_hash = hash_password(payload.new_password)
        revoke_all_refresh_tokens(db, user.id)
    db.commit()
    db.refresh(user)
    return user


@app.get("/api/v1/videos/{video_id}/stream")
def stream_video(
    video_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Phát video (hỗ trợ HTTP Range để tua nhanh)."""
    video = db.get(Video, video_id)
    visible = video is not None and not video.is_deleted and (
        video.status == VideoStatus.published
        or video.owner_id == user.id
        or user.role in {UserRole.moderator, UserRole.admin}
    )
    if not visible:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    path = Path(video.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Tệp video không tồn tại trên máy chủ")
    return FileResponse(path, media_type=video.mime_type)


def _label_infos(video: Video) -> list[VideoLabelInfo]:
    return [
        VideoLabelInfo(name=item.label.name, confidence=item.confidence, level=item.level)
        for item in video.labels
    ]


# UC009 — lọc và tìm kiếm video theo nhãn
@app.get("/api/v1/videos/search", response_model=list[VideoSearchItem])
def search_videos(
    label: str | None = None,
    exclude_label: str | None = None,
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[VideoSearchItem]:
    """Tìm video theo caption và/hoặc lọc theo nhãn (kèm loại trừ nhãn)."""
    query = select(Video).where(Video.is_deleted.is_(False))
    if user.role not in {UserRole.moderator, UserRole.admin}:
        query = query.where(or_(Video.status == VideoStatus.published, Video.owner_id == user.id))
    if q and q.strip():
        query = query.where(Video.caption.ilike(f"%{q.strip()}%"))
    if label and label.strip():
        query = query.where(
            Video.id.in_(
                select(VideoLabel.video_id)
                .join(Label, Label.id == VideoLabel.label_id)
                .where(Label.name.ilike(label.strip()))
            )
        )
    if exclude_label and exclude_label.strip():
        query = query.where(
            ~Video.id.in_(
                select(VideoLabel.video_id)
                .join(Label, Label.id == VideoLabel.label_id)
                .where(Label.name.ilike(exclude_label.strip()))
            )
        )
    videos = list(db.scalars(query.order_by(Video.created_at.desc()).limit(limit)))
    return [
        VideoSearchItem(
            id=video.id,
            original_filename=video.original_filename,
            caption=video.caption,
            status=video.status,
            owner_display_name=video.owner.display_name,
            labels=_label_infos(video),
            created_at=video.created_at,
        )
        for video in videos
    ]


def _apply_labels(db: Session, video: Video, items) -> None:
    """Thay toàn bộ nhãn của video (multi-label) sau khi validate danh sách."""
    resolved: dict[str, Label] = {}
    for item in items:
        name = item.name.strip()
        key = name.lower()
        if key in resolved:
            raise HTTPException(status_code=400, detail="Danh sách nhãn có mục trùng lặp")
        label = db.scalar(select(Label).where(Label.name.ilike(name)))
        if label is None:
            raise HTTPException(
                status_code=400,
                detail=f"Nhãn '{name}' chưa tồn tại, quản trị viên cần tạo trước",
            )
        if not label.is_active:
            raise HTTPException(status_code=400, detail=f"Nhãn '{name}' đã bị vô hiệu hóa")
        resolved[key] = label
    for existing in list(video.labels):
        db.delete(existing)
    db.flush()
    for item in items:
        label = resolved[item.name.strip().lower()]
        db.add(
            VideoLabel(
                video_id=video.id,
                label_id=label.id,
                confidence=item.confidence,
                level=confidence_level(item.confidence),
            )
        )


# UC007/UC015 — xác nhận và chỉnh sửa nhãn
@app.post("/api/v1/videos/{video_id}/labels/confirm", response_model=list[VideoLabelInfo])
def confirm_labels(
    video_id: UUID,
    payload: LabelsUpdateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[VideoLabelInfo]:
    """Chủ video xác nhận hoặc chỉnh sửa nhãn (UC007). Không đổi trạng thái đăng."""
    video = db.get(Video, video_id)
    if video is None or video.is_deleted or video.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    _apply_labels(db, video, payload.labels)
    db.commit()
    db.refresh(video)
    return _label_infos(video)


@app.patch("/api/v1/videos/{video_id}/labels", response_model=list[VideoLabelInfo])
def edit_labels(
    video_id: UUID,
    payload: LabelsUpdateRequest,
    user: User = Depends(require_roles(UserRole.moderator, UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[VideoLabelInfo]:
    """Moderator/Admin thay thế toàn bộ nhãn của một video (UC015)."""
    video = db.get(Video, video_id)
    if video is None or video.is_deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    _apply_labels(db, video, payload.labels)
    db.commit()
    db.refresh(video)
    return _label_infos(video)


def _appeal_response(appeal: Appeal, user_display_name: str) -> AppealResponse:
    return AppealResponse(
        id=appeal.id,
        video_id=appeal.video_id,
        user_id=appeal.user_id,
        user_display_name=user_display_name,
        reason=appeal.reason,
        status=appeal.status,
        moderator_id=appeal.moderator_id,
        decision_reason=appeal.decision_reason,
        created_at=appeal.created_at,
        decided_at=appeal.decided_at,
    )


# UC011/UC017 — quy trình khiếu nại (appeal)
@app.post(
    "/api/v1/videos/{video_id}/appeals",
    response_model=AppealResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_appeal(
    video_id: UUID,
    payload: AppealCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> AppealResponse:
    video = db.get(Video, video_id)
    if video is None or video.is_deleted or video.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    if video.status != VideoStatus.rejected:
        raise HTTPException(status_code=400, detail="Chỉ video bị từ chối mới được yêu cầu xem xét lại")
    existing = db.scalar(
        select(Appeal).where(
            Appeal.video_id == video.id,
            Appeal.user_id == user.id,
            Appeal.status == AppealStatus.open,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Bạn đã có yêu cầu xem xét lại đang chờ xử lý cho video này",
        )
    appeal = Appeal(video_id=video.id, user_id=user.id, reason=payload.reason)
    db.add(appeal)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Bạn đã có yêu cầu xem xét lại đang chờ xử lý cho video này",
        ) from exc
    db.refresh(appeal)
    return _appeal_response(appeal, user.display_name)


@app.get("/api/v1/moderation/appeals", response_model=list[AppealResponse])
def list_appeals(
    status_filter: AppealStatus | None = Query(default=None, alias="status"),
    user: User = Depends(require_roles(UserRole.moderator, UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[AppealResponse]:
    query = select(Appeal)
    if status_filter is not None:
        query = query.where(Appeal.status == status_filter)
    else:
        query = query.where(Appeal.status == AppealStatus.open)
    appeals = list(db.scalars(query.order_by(Appeal.created_at.asc())))
    if not appeals:
        return []
    user_ids = {appeal.user_id for appeal in appeals}
    names = {
        row.id: row.display_name
        for row in db.scalars(select(User).where(User.id.in_(user_ids)))
    }
    return [_appeal_response(appeal, names.get(appeal.user_id, "")) for appeal in appeals]


@app.post(
    "/api/v1/moderation/appeals/{appeal_id}/decision",
    status_code=status.HTTP_204_NO_CONTENT,
)
def appeal_decision(
    appeal_id: UUID,
    payload: AppealDecisionRequest,
    user: User = Depends(require_roles(UserRole.moderator, UserRole.admin)),
    db: Session = Depends(get_db),
) -> None:
    appeal = db.get(Appeal, appeal_id)
    if appeal is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu xem xét lại")
    if appeal.status != AppealStatus.open:
        raise HTTPException(status_code=409, detail="Yêu cầu này đã được xử lý")
    video = db.get(Video, appeal.video_id)
    appeal.moderator_id = user.id
    appeal.decision_reason = payload.reason
    appeal.decided_at = datetime.now(timezone.utc)
    if payload.action == ModerationAction.approve:
        appeal.status = AppealStatus.approved
        if video is not None and not video.is_deleted:
            video.status = VideoStatus.published
    else:
        appeal.status = AppealStatus.rejected
    db.commit()


# 2.2.12/2.2.13 — quản lý video và nhãn nội dung phía Admin
@app.patch("/api/v1/admin/videos/{video_id}/status", response_model=VideoResponse)
def admin_update_video_status(
    video_id: UUID,
    payload: AdminVideoStatusUpdate,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> Video:
    video = db.get(Video, video_id)
    if video is None or video.is_deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    if payload.status == "deleted":
        video.is_deleted = True
        video.status = VideoStatus.deleted
    else:
        video.status = VideoStatus(payload.status)
    db.commit()
    db.refresh(video)
    return video


def _admin_label_response(db: Session, label: Label) -> AdminLabelResponse:
    count = db.scalar(
        select(func.count()).select_from(VideoLabel).where(VideoLabel.label_id == label.id)
    )
    return AdminLabelResponse(
        id=label.id,
        name=label.name,
        is_active=label.is_active,
        video_count=int(count or 0),
    )


@app.get("/api/v1/admin/labels", response_model=list[AdminLabelResponse])
def admin_list_labels(
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[AdminLabelResponse]:
    labels = list(db.scalars(select(Label).order_by(Label.name.asc())))
    return [_admin_label_response(db, label) for label in labels]


@app.post(
    "/api/v1/admin/labels",
    response_model=AdminLabelResponse,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_label(
    payload: AdminLabelCreate,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> AdminLabelResponse:
    name = payload.name.strip()
    if db.scalar(select(Label).where(Label.name.ilike(name))):
        raise HTTPException(status_code=409, detail="Nhãn này đã tồn tại")
    label = Label(name=name)
    db.add(label)
    db.commit()
    db.refresh(label)
    return _admin_label_response(db, label)


@app.patch("/api/v1/admin/labels/{label_id}", response_model=AdminLabelResponse)
def admin_update_label(
    label_id: UUID,
    payload: AdminLabelUpdate,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> AdminLabelResponse:
    label = db.get(Label, label_id)
    if label is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhãn")
    if payload.name is not None:
        name = payload.name.strip()
        conflict = db.scalar(select(Label).where(Label.name.ilike(name), Label.id != label.id))
        if conflict is not None:
            raise HTTPException(status_code=409, detail="Nhãn này đã tồn tại")
        label.name = name
    if payload.is_active is not None:
        label.is_active = payload.is_active
    db.commit()
    db.refresh(label)
    return _admin_label_response(db, label)


# UC019/UC020 — thống kê hiệu suất Moderator và dashboard hệ thống
@app.get(
    "/api/v1/admin/moderators/{moderator_id}/stats",
    response_model=ModeratorStatsResponse,
)
def moderator_stats(
    moderator_id: UUID,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> ModeratorStatsResponse:
    target = db.get(User, moderator_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    if target.role not in {UserRole.moderator, UserRole.admin}:
        raise HTTPException(status_code=400, detail="Người dùng không phải Moderator/Admin")
    approved = int(
        db.scalar(
            select(func.count())
            .select_from(ModerationReview)
            .where(
                ModerationReview.moderator_id == target.id,
                ModerationReview.action == ModerationAction.approve,
            )
        )
        or 0
    )
    rejected = int(
        db.scalar(
            select(func.count())
            .select_from(ModerationReview)
            .where(
                ModerationReview.moderator_id == target.id,
                ModerationReview.action == ModerationAction.reject,
            )
        )
        or 0
    )
    appeals = int(
        db.scalar(
            select(func.count()).select_from(Appeal).where(Appeal.moderator_id == target.id)
        )
        or 0
    )
    return ModeratorStatsResponse(
        moderator_id=target.id,
        display_name=target.display_name,
        role=target.role,
        videos_reviewed=approved + rejected,
        reviews_approved=approved,
        reviews_rejected=rejected,
        appeals_handled=appeals,
    )


def _status_counts(rows, enum_cls) -> dict[str, int]:
    counts = {item.value: 0 for item in enum_cls}
    for value, count in rows:
        key = value.value if hasattr(value, "value") else str(value)
        counts[key] = int(count)
    return counts


@app.get("/api/v1/admin/stats", response_model=SystemStatsResponse)
def admin_stats(
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> SystemStatsResponse:
    """Dashboard UC020: số video theo trạng thái, phân bố nhãn, report/appeal,
    job AI và khối lượng công việc của từng Moderator trong `days` ngày."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    videos = list(db.scalars(select(Video).where(Video.created_at >= since)))
    videos_by_status = _status_counts(
        db.execute(
            select(Video.status, func.count())
            .where(Video.created_at >= since)
            .group_by(Video.status)
        ).all(),
        VideoStatus,
    )

    label_rows = db.execute(
        select(Label.name, func.count(VideoLabel.id))
        .join(VideoLabel, VideoLabel.label_id == Label.id)
        .join(Video, Video.id == VideoLabel.video_id)
        .where(Video.created_at >= since, Video.is_deleted.is_(False))
        .group_by(Label.name)
        .order_by(func.count(VideoLabel.id).desc())
    ).all()
    total_videos = len(videos)
    labels = [
        {
            "name": name,
            "video_count": int(count),
            "ratio": round(int(count) / total_videos, 4) if total_videos else 0.0,
        }
        for name, count in label_rows
    ]

    reports_by_status = _status_counts(
        db.execute(
            select(Report.status, func.count())
            .where(Report.created_at >= since)
            .group_by(Report.status)
        ).all(),
        ReportStatus,
    )
    appeals_by_status = _status_counts(
        db.execute(
            select(Appeal.status, func.count())
            .where(Appeal.created_at >= since)
            .group_by(Appeal.status)
        ).all(),
        AppealStatus,
    )
    jobs_by_status = _status_counts(
        db.execute(
            select(AIJob.status, func.count())
            .where(AIJob.created_at >= since)
            .group_by(AIJob.status)
        ).all(),
        JobStatus,
    )

    workload_rows = db.execute(
        select(ModerationReview.moderator_id, User.display_name, func.count())
        .join(User, User.id == ModerationReview.moderator_id)
        .where(ModerationReview.created_at >= since)
        .group_by(ModerationReview.moderator_id, User.display_name)
        .order_by(func.count().desc())
    ).all()

    return SystemStatsResponse(
        days=days,
        videos_total=total_videos,
        videos_by_status=videos_by_status,
        labels=labels,
        reports_by_status=reports_by_status,
        appeals_by_status=appeals_by_status,
        jobs_by_status=jobs_by_status,
        moderator_workload=[
            {
                "moderator_id": moderator_id,
                "display_name": display_name,
                "reviews": int(count),
            }
            for moderator_id, display_name, count in workload_rows
        ],
    )
