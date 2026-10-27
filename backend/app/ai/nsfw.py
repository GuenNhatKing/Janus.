"""Adapter tích hợp NSFW-Detection (pipeline Adult) vào backend.

Pipeline được chạy như một tiến trình con bằng интерpreter do cấu hình chỉ định,
thay vì import TensorFlow/PyTorch vào process của API. Nhờ vậy backend không bị
phụ thuộc vào các thư viện nặng và vẫn chạy được khi môi trường AI chưa cài.

Đầu ra đọc từ ``<out_dir>/<tên file video>/08_final_decision.json`` do
``proposed/proposed_adult_video_detect.py`` ghi ra.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

from app.ai.base import AnalysisReport, Detection, DetectorUnavailableError
from app.config import get_settings

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
# Thư mục chứa code backend — đường dẫn tương đối trong NSFW_PIPELINE_DIR được
# giải phóng dựa trên thư mục này.
BACKEND_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_SCRIPT = Path("proposed") / "proposed_adult_video_detect.py"
FINAL_DECISION_JSON = "08_final_decision.json"
REQUIRED_MODULES = ("tensorflow", "torch", "cv2", "numpy")
MODEL_FILES = (
    Path("models") / "mobilenetv3_small_adult_normal.keras",
    Path("models") / "resnet50_adult_normal_fcn_layer4_classifier.pth",
)

_preflight_cache: tuple[bool, str] | None = None


def pipeline_dir() -> Path:
    """Thư mục ``backend/NSFW-Detection/src`` chứa script pipeline và các model."""
    configured = get_settings().nsfw_pipeline_dir
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else (BACKEND_ROOT / path)
    return BACKEND_ROOT / "NSFW-Detection" / "src"


def _interpreter() -> str:
    return get_settings().nsfw_python or sys.executable


def _check_preflight() -> tuple[bool, str]:
    """Trả về (được không, lý do) — kiểm tra môi trường mà không import nặng."""
    src = pipeline_dir()
    script = src / PIPELINE_SCRIPT
    if not script.exists():
        return False, f"không tìm thấy script pipeline tại {script}"

    missing_models = [str(src / name) for name in MODEL_FILES if not (src / name).exists()]
    if missing_models:
        return False, "thiếu file model: " + ", ".join(missing_models)

    probe = (
        "import importlib.util as u, json, sys;"
        "print(json.dumps([m for m in sys.argv[1:] if u.find_spec(m) is None]))"
    )
    try:
        proc = subprocess.run(
            [_interpreter(), "-c", probe, *REQUIRED_MODULES],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"không chạy được interpreter {_interpreter()}: {exc}"

    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "lỗi không xác định khi kiểm tra môi trường").strip()

    missing = json.loads(proc.stdout.strip() or "[]")
    if missing:
        return False, "chưa cài thư viện: " + ", ".join(missing)
    return True, ""


def preflight(reset_cache: bool = False) -> tuple[bool, str]:
    """Kiểm tra môi trường NSFW-Detection, kết quả được cache trong mỗi process."""
    global _preflight_cache
    if _preflight_cache is None or reset_cache:
        _preflight_cache = _check_preflight()
        if not _preflight_cache[0]:
            logger.warning("NSFW-Detection chưa sẵn sàng: %s", _preflight_cache[1])
    return _preflight_cache


def _confidence_from_summary(summary: dict) -> float:
    """Điểm tin cậy của phán quyết cuối cùng, suy ra từ các anchor đã đánh giá.

    - ADULT: lấy anchor có độ tin cậy cao nhất theo nhánh yếu hơn (min của
      p_mobile và p_resnet) — hai nhánh phải cùng đồng tình thì mới tin.
    - NORMAL: độ tin cậy = 1 - xác suất vi phạm cao nhất quan sát được.
    """
    anchors = summary.get("anchor_details") or []
    if not anchors:
        # Không đánh giá được anchor nào (video không trích xuất được frame):
        # không có bằng chứng, nên trả về độ tin cậy trung tính 0.5.
        return 0.5

    scores = []
    for anchor in anchors:
        p_mobile = float(anchor.get("p_mobile") or 0.0)
        p_resnet = float(anchor.get("p_resnet_anchor") or 0.0)
        if anchor.get("decision") == "ADULT":
            scores.append(min(p_mobile, p_resnet))

    if summary.get("final_decision") == "ADULT":
        confidence = max(scores, default=0.0)
    else:
        worst = 0.0
        for anchor in anchors:
            p_mobile = float(anchor.get("p_mobile") or 0.0)
            p_resnet = float(anchor.get("p_resnet_anchor") or 0.0)
            worst = max(worst, p_mobile, p_resnet)
        confidence = 1.0 - worst

    return round(min(max(confidence, 0.0), 1.0), 4)


def analyse(video_path: Path) -> AnalysisReport:
    """Chạy pipeline NSFW-Detection trên một file video và trả về báo cáo."""
    ready, reason = preflight()
    if not ready:
        raise DetectorUnavailableError(reason)

    video_path = Path(video_path).resolve()
    if not video_path.exists():
        raise DetectorUnavailableError(f"không tìm thấy file video {video_path}")

    settings = get_settings()
    with tempfile.TemporaryDirectory(prefix="nsfw-detection-") as out_dir:
        command = [
            _interpreter(),
            str(pipeline_dir() / PIPELINE_SCRIPT),
            "--video",
            str(video_path),
            "--out_dir",
            out_dir,
        ]
        try:
            proc = subprocess.run(
                command,
                cwd=str(pipeline_dir()),
                capture_output=True,
                text=True,
                timeout=settings.nsfw_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise DetectorUnavailableError(
                f"pipeline quá thời gian {settings.nsfw_timeout_seconds}s"
            ) from exc
        except OSError as exc:
            raise DetectorUnavailableError(f"không chạy được pipeline: {exc}") from exc

        if proc.returncode != 0:
            tail = "\n".join((proc.stderr or proc.stdout or "").splitlines()[-15:])
            raise RuntimeError(f"NSFW-Detection thoát với mã {proc.returncode}: {tail}")

        json_path = Path(out_dir) / video_path.stem / FINAL_DECISION_JSON
        if not json_path.exists():
            raise RuntimeError(f"pipeline không ghi ra {json_path.name}")
        summary = json.loads(json_path.read_text(encoding="utf-8"))

    decision = str(summary.get("final_decision") or "NORMAL").upper()
    confidence = _confidence_from_summary(summary)
    anchors = summary.get("total_anchors_evaluated")
    timings = summary.get("video_metadata") or {}

    lines = [
        (
            "[NSFW-Detection] phán quyết: {decision} | độ tin cậy: {conf:.2f} | "
            "anchor đã đánh giá: {anchors} | fps: {fps}"
        ).format(
            decision=decision,
            conf=confidence,
            anchors=anchors if anchors is not None else "không xác định",
            fps=timings.get("fps"),
        ),
        "[Speech-to-Text] chưa được triển khai — chưa có transcript âm thanh.",
    ]

    if decision == "ADULT":
        return AnalysisReport(
            detections=[Detection(label="Adult", confidence=confidence, detector="nsfw")],
            normal_confidence=0.0,
            transcript="\n".join(lines),
            source="nsfw-detection",
        )
    return AnalysisReport(
        detections=[],
        normal_confidence=confidence,
        transcript="\n".join(lines),
        source="nsfw-detection",
    )
