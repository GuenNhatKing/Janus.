"""Test tích hợp NSFW-Detection và pipeline AI của backend."""

import pytest

from app.services import ai_service as services
from app.ai import nsfw
from app.ai.base import (
    SAFE_LABEL,
    AnalysisReport,
    Detection,
    DetectorNotImplementedError,
    DetectorUnavailableError,
)
from app.ai.placeholders import DETECTORS
from app.ai.pipeline import analyse_video
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import AIJob, JobStatus, User, Video, VideoStatus
from app.core.security import hash_password


def test_placeholder_detectors_raise_and_model_dirs_exist():
    for name, detector in DETECTORS.items():
        with pytest.raises(DetectorNotImplementedError):
            detector("clip.mp4")
        # Placeholder detectors do not require model directories until their
        # implementations and model assets are supplied.


def test_confidence_is_derived_from_anchor_scores():
    adult = {
        "final_decision": "ADULT",
        "anchor_details": [
            {"decision": "ADULT", "p_mobile": 0.9, "p_resnet_anchor": 0.8},
            {"decision": "NORMAL", "p_mobile": 0.1, "p_resnet_anchor": 0.2},
        ],
    }
    normal = {
        "final_decision": "NORMAL",
        "anchor_details": [{"decision": "NORMAL", "p_mobile": 0.2, "p_resnet_anchor": 0.3}],
    }
    assert nsfw._confidence_from_summary(adult) == pytest.approx(0.8)
    assert nsfw._confidence_from_summary(normal) == pytest.approx(0.7)
    assert nsfw._confidence_from_summary({"final_decision": "NORMAL"}) == pytest.approx(0.5)


def test_pipeline_records_unimplemented_detectors(monkeypatch, tmp_path):
    stub = AnalysisReport(
        detections=[],
        normal_confidence=0.9,
        transcript="[NSFW-Detection] phán quyết: NORMAL",
        source="nsfw-detection",
    )
    monkeypatch.setattr(nsfw, "analyse", lambda path: stub)

    report = analyse_video(tmp_path / "clip.mp4")

    assert report.normal_confidence == 0.9
    assert len(report.skipped) == len(DETECTORS)
    assert any("[Chưa triển khai]" in line for line in report.transcript.splitlines())


def _seed_job(tmp_path) -> tuple:
    with SessionLocal() as db:
        user = User(
            email="job-owner@example.com",
            display_name="Job Owner",
            password_hash=hash_password("password123"),
        )
        db.add(user)
        db.flush()
        video = Video(
            owner_id=user.id,
            original_filename="clip.mp4",
            storage_path=str(tmp_path / "clip.mp4"),
            mime_type="video/mp4",
            size_bytes=10,
        )
        db.add(video)
        db.flush()
        job = AIJob(video_id=video.id)
        db.add(job)
        db.commit()
        return video.id, job.id


def _unavailable(path) -> AnalysisReport:
    raise DetectorUnavailableError("chưa cài tensorflow")


def test_analysis_falls_back_to_mock_when_ai_unavailable(monkeypatch, tmp_path):
    video_id, job_id = _seed_job(tmp_path)
    monkeypatch.setattr(services, "analyse_video", _unavailable)

    services.run_video_analysis(video_id)

    with SessionLocal() as db:
        job = db.get(AIJob, job_id)
        video = db.get(Video, video_id)
        assert job.status is JobStatus.succeeded
        assert video.status is VideoStatus.published
        assert "chưa sẵn sàng" in job.transcript
        assert {video_label.label.name for video_label in video.labels} == {SAFE_LABEL}


def test_analysis_required_mode_marks_job_failed(monkeypatch, tmp_path):
    video_id, job_id = _seed_job(tmp_path)
    monkeypatch.setattr(services, "analyse_video", _unavailable)
    required = get_settings().model_copy(update={"ai_analysis_mode": "required"})
    monkeypatch.setattr(services, "get_settings", lambda: required)

    services.run_video_analysis(video_id)

    with SessionLocal() as db:
        job = db.get(AIJob, job_id)
        video = db.get(Video, video_id)
        assert job.status is JobStatus.failed
        assert "chưa cài tensorflow" in job.error_message
        assert video.status is VideoStatus.failed


def test_analysis_persists_adult_detection_into_moderation_queue(monkeypatch, tmp_path):
    video_id, job_id = _seed_job(tmp_path)
    report = AnalysisReport(
        detections=[Detection(label="Adult", confidence=0.87, detector="nsfw")],
        normal_confidence=0.0,
        transcript="[NSFW-Detection] phán quyết: ADULT",
        source="nsfw-detection",
    )
    monkeypatch.setattr(services, "analyse_video", lambda path: report)

    services.run_video_analysis(video_id)

    with SessionLocal() as db:
        job = db.get(AIJob, job_id)
        video = db.get(Video, video_id)
        assert job.status is JobStatus.succeeded
        assert video.status is VideoStatus.pending_review
        labels = {video_label.label.name: video_label for video_label in video.labels}
        assert set(labels) == {"Adult"}
        assert labels["Adult"].confidence == pytest.approx(0.87)
        assert labels["Adult"].level == "HIGH"


def test_analysis_publishes_safe_video(monkeypatch, tmp_path):
    video_id, job_id = _seed_job(tmp_path)
    report = AnalysisReport(
        detections=[],
        normal_confidence=0.92,
        transcript="[NSFW-Detection] phán quyết: NORMAL",
        source="nsfw-detection",
    )
    monkeypatch.setattr(services, "analyse_video", lambda path: report)

    services.run_video_analysis(video_id)

    with SessionLocal() as db:
        job = db.get(AIJob, job_id)
        video = db.get(Video, video_id)
        assert job.status is JobStatus.succeeded
        assert video.status is VideoStatus.published
        assert {video_label.label.name for video_label in video.labels} == {SAFE_LABEL}
