from pathlib import Path
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AIJob, JobStatus, Label, Video, VideoLabel, VideoStatus


def confidence_level(score: float) -> str:
    settings = get_settings()
    if score < settings.low_confidence_threshold:
        return "LOW"
    if score < settings.high_confidence_threshold:
        return "MEDIUM"
    return "HIGH"


def run_mock_analysis(video_id: UUID) -> None:
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        job = db.scalar(select(AIJob).where(AIJob.video_id == video_id).order_by(AIJob.created_at.desc()))
        video = db.get(Video, video_id)
        if job is None or video is None:
            return
        job.status = JobStatus.running
        db.commit()
        job.transcript = "Mock transcript for development testing."
        safe_label = db.scalar(select(Label).where(Label.name == "Safe"))
        if safe_label is None:
            safe_label = Label(name="Safe")
            db.add(safe_label)
            db.flush()
        db.add(VideoLabel(video_id=video.id, label_id=safe_label.id, confidence=0.95, level=confidence_level(0.95)))
        job.status = JobStatus.succeeded
        job.completed_at = datetime.now(timezone.utc)
        video.status = VideoStatus.published
        db.commit()
    except Exception as exc:
        db.rollback()
        if job is not None:
            job.status = JobStatus.failed
            job.error_message = str(exc)
            video.status = VideoStatus.failed
            db.commit()
    finally:
        db.close()


def remove_local_file(path: str) -> None:
    Path(path).unlink(missing_ok=True)
