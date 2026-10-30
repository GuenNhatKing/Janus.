import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import AIJob, JobStatus, Label, Video, VideoLabel, VideoStatus

logger = logging.getLogger(__name__)

SUPPORTED_MP4_CODECS = (b"avc1", b"hvc1", b"hev1", b"av01", b"mp4v")
MOCK_TRANSCRIPT = "Mock transcript for development testing."


def validate_mp4_content(content: bytes) -> str:
    if len(content) < 16 or content[4:8] != b"ftyp":
        raise ValueError("Tệp không có MP4 magic bytes hợp lệ")
    box_size = int.from_bytes(content[0:4], "big")
    if box_size < 16 or box_size > len(content):
        raise ValueError("MP4 ftyp box không hợp lệ")
    compatible_brands = content[8:box_size]
    if not any(
        brand in compatible_brands
        for brand in (b"isom", b"iso2", b"mp41", b"mp42", b"avc1")
    ):
        raise ValueError("MP4 brand không được hỗ trợ")
    codec = next((marker for marker in SUPPORTED_MP4_CODECS if marker in content), None)
    if codec is None:
        raise ValueError("Không tìm thấy codec video MP4 được hỗ trợ")
    return codec.decode("ascii")


def confidence_level(score: float) -> str:
    settings = get_settings()
    if score < settings.low_confidence_threshold:
        return "LOW"
    if score < settings.high_confidence_threshold:
        return "MEDIUM"
    return "HIGH"


def run_mock_analysis(video_id: UUID) -> None:
    db = SessionLocal()
    job: AIJob | None = None
    video: Video | None = None
    try:
        job = db.scalar(
            select(AIJob)
            .where(AIJob.video_id == video_id)
            .order_by(AIJob.created_at.desc())
        )
        video = db.get(Video, video_id)
        if job is None or video is None:
            return
        job.status = JobStatus.running
        db.commit()
        handler(db, job, video)
    except Exception as exc:
        db.rollback()
        logger.exception("Job AI cho video %s thất bại", video_id)
        if job is not None:
            job.status = JobStatus.failed
            job.error_message = str(exc)
            if video is not None:
                video.status = VideoStatus.failed
            db.commit()
    finally:
        db.close()


def run_mock_analysis(video_id: UUID, note: str | None = None) -> None:
    """Giữ nguyên hành vi mock cũ (dùng khi AI bị tắt hoặc môi trường AI chưa sẵn sàng)."""

    def handler(db: Session, job: AIJob, video: Video) -> None:
        _apply_mock_result(db, job, video, note)

    _run_job(video_id, handler)


def run_video_analysis(video_id: UUID) -> None:
    """Điểm vào của BackgroundTasks: chạy NSFW-Detection theo ``AI_ANALYSIS_MODE``."""

    def handler(db: Session, job: AIJob, video: Video) -> None:
        settings = get_settings()
        mode = settings.ai_analysis_mode.strip().lower()
        if mode not in {"auto", "required", "off"}:
            raise ValueError(
                f"AI_ANALYSIS_MODE không hợp lệ: {settings.ai_analysis_mode!r}"
            )

        report: AnalysisReport | None = None
        if mode != "off":
            try:
                report = analyse_video(Path(video.storage_path))
            except DetectorUnavailableError as exc:
                if mode == "required":
                    raise
                logger.warning(
                    "NSFW-Detection chưa sẵn sàng, dùng kết quả mock: %s", exc
                )
                note = f"[NSFW-Detection chưa sẵn sàng: {exc}]"
                _apply_mock_result(db, job, video, note)
                return

        if report is None:
            _apply_mock_result(db, job, video)
            return
        _apply_analysis_report(db, job, video, report)

    _run_job(video_id, handler)


def remove_local_file(path: str) -> None:
    Path(path).unlink(missing_ok=True)


def as_aware(value: datetime) -> datetime:
    """SQLite trả datetime naive; chuẩn hoá về UTC để so sánh an toàn."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def issue_refresh_token(db: Session, user: User) -> str:
    """Tạo refresh token mới (chỉ lưu băm) và trả về giá trị thô cho client."""
    settings = get_settings()
    raw = new_opaque_token(48)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_opaque_token(raw),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    return raw


def revoke_refresh_token(
    db: Session, raw_token: str, user_id: UUID | None = None
) -> bool:
    """Thu hồi một refresh token; trả về True nếu tìm thấy và còn hiệu lực."""
    row = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_opaque_token(raw_token)
        )
    )
    if row is None or row.revoked_at is not None:
        return False
    if user_id is not None and row.user_id != user_id:
        return False
    row.revoked_at = datetime.now(timezone.utc)
    return True


def revoke_all_refresh_tokens(db: Session, user_id: UUID) -> None:
    now = datetime.now(timezone.utc)
    rows = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
        )
    )
    for row in rows:
        row.revoked_at = now


def purge_expired_revoked_tokens(db: Session) -> None:
    """Dọn access token đã hết hạn khỏi bảng thu hồi."""
    db.execute(
        delete(RevokedToken).where(RevokedToken.expires_at < datetime.now(timezone.utc))
    )
