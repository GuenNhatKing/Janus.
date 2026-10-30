"""Placeholder cho các bộ nhận diện chưa được triển khai.

Mỗi hàm dưới đây là điểm gọi (entry point) tương ứng với một detector sẽ được
nối vào pipeline. Khi được gọi, hàm raise ``DetectorNotImplementedError`` để
người gọi biết rõ đây là chức năng chưa triển khai, đồng thời dẫn tới thư mục
model dành cho detector đó.

Thư mục model placeholder (chưa chứa weight):
    backend/NSFW-Detection/src/models/violence/
    backend/NSFW-Detection/src/models/sound/
    backend/NSFW-Detection/src/models/text/
"""

from __future__ import annotations

from pathlib import Path

from app.ai.base import AnalysisReport, DetectorNotImplementedError
from app.ai.nsfw import pipeline_dir

# Thư mục chứa model của pipeline NSFW-Detection (adult) và các detector tương lai.
MODEL_ROOT = pipeline_dir() / "models"


def model_dir(name: str) -> Path:
    """Thư mục model của một detector (đang là placeholder, chưa có weight)."""
    return MODEL_ROOT / name


def detect_violence(video_path: Path) -> AnalysisReport:
    """Nhận diện bạo lực/gore trong khung hình video — chưa triển khai."""
    raise DetectorNotImplementedError(
        f"bộ nhận diện Violence chưa được triển khai (model sẽ đặt tại {model_dir('violence')})"
    )


def detect_sound(video_path: Path) -> AnalysisReport:
    """Nhận diện âm thanh không phù hợp (Audio Analysis) — chưa triển khai."""
    raise DetectorNotImplementedError(
        f"bộ nhận diện Sound/Audio chưa được triển khai (model sẽ đặt tại {model_dir('sound')})"
    )


def detect_text(video_path: Path) -> AnalysisReport:
    """Phân tích nội dung lời nói sau Speech-to-Text — chưa triển khai."""
    raise DetectorNotImplementedError(
        f"bộ nhận diện Text (Speech-to-Text + Text Analysis) chưa được triển khai "
        f"(model sẽ đặt tại {model_dir('text')})"
    )


DETECTORS = {
    "violence": detect_violence,
    "sound": detect_sound,
    "text": detect_text,
}
