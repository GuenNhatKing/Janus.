"""Pipeline phân tích nội dung: lắp ráp kết quả từ các detector.

Thứ tự theo SRS (2.2.5): Visual Analysis -> Audio Analysis -> Speech-to-Text ->
Text Analysis -> Multi-label Classification -> Confidence Score.

Hiện chỉ có Visual Analysis (Adult) là chạy thật qua NSFW-Detection; các detector
còn lại là placeholder, được ghi vào ``AnalysisReport.skipped`` thay vì làm hỏng
toàn bộ job.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.ai import nsfw
from app.ai.base import AnalysisReport, DetectorNotImplementedError
from app.ai.placeholders import DETECTORS

logger = logging.getLogger(__name__)


def analyse_video(video_path: Path) -> AnalysisReport:
    """Chạy toàn bộ detector trên một file video.

    - ``DetectorUnavailableError`` được đẩy lên cho service quyết định cách xử lý
      theo ``AI_ANALYSIS_MODE``.
    - ``DetectorNotImplementedError`` (placeholder) được ghi lại vào ``skipped``.
    """
    report = nsfw.analyse(Path(video_path))

    skipped: list[str] = []
    for name, detector in DETECTORS.items():
        try:
            detector(Path(video_path))
        except DetectorNotImplementedError as exc:
            logger.info("Bỏ qua detector %s: %s", name, exc)
            skipped.append(f"{name}: {exc}")
        except NotImplementedError as exc:  # placeholder dùng NotImplementedError thuần
            skipped.append(f"{name}: {exc}")

    report.skipped = skipped
    if skipped:
        report.transcript += "\n" + "\n".join(f"[Chưa triển khai] {item}" for item in skipped)
    return report
