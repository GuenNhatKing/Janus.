"""Thumbnail extraction for uploaded videos."""

from pathlib import Path

import cv2


def extract_first_frame(video_path: Path) -> bytes:
    capture = cv2.VideoCapture(str(video_path))
    try:
        if not capture.isOpened():
            raise ValueError(f"Không thể mở video để trích xuất thumbnail: {video_path}")

        success, frame = capture.read()
        if not success or frame is None:
            capture.set(cv2.CAP_PROP_POS_MSEC, 500)
            success, frame = capture.read()
        if not success or frame is None:
            raise ValueError("Không đọc được frame video để tạo thumbnail")

        encoded, buffer = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), 85],
        )
        if not encoded:
            raise ValueError("Không thể encode frame video thành JPEG")
        return buffer.tobytes()
    finally:
        capture.release()
