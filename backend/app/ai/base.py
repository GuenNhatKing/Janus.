"""Khung dữ liệu dùng chung cho các bộ phân tích nội dung (detector).

Mỗi detector trả về danh sách nhãn rủi ro phát hiện được. Việc lắp ráp thành
kết quả AI của một video nằm trong ``app.ai.pipeline``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SAFE_LABEL = "Safe"


@dataclass(frozen=True)
class Detection:
    """Một nhãn rủi ro được một detector đề xuất cho video."""

    label: str
    confidence: float
    detector: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence phải nằm trong [0, 1], nhận được {self.confidence}")


class DetectorUnavailableError(RuntimeError):
    """Detector đã có mã nguồn nhưng không chạy được (thiếu thư viện/model/thiết bị)."""


class DetectorNotImplementedError(NotImplementedError):
    """Detector là placeholder, chưa được triển khai."""


@dataclass
class AnalysisReport:
    """Kết quả phân tích của một video."""

    detections: list[Detection] = field(default_factory=list)
    normal_confidence: float = 0.5
    transcript: str = ""
    skipped: list[str] = field(default_factory=list)
    source: str = "unknown"

    @property
    def is_safe(self) -> bool:
        return not self.detections
