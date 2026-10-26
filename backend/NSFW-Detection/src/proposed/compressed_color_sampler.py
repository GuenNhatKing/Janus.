import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class CompressedColorSampler:
    """
    Bộ lấy mẫu chỉ dựa trên đặc trưng màu HSV và khoảng cách Bhattacharyya.
    Không trích xuất I-frame, không dùng ffprobe và không dùng mô hình học sâu.

    Chọn frame khi:
      - Đây là frame đầu tiên;
      - Đã cách frame được chọn trước đó ít nhất delta_t giây;
      - Khoảng cách Bhattacharyya có Z-score vượt z_threshold.

    Ranh giới cảnh được ước lượng từ khoảng cách HSV lớn; đây là heuristic,
    không tương đương bộ phát hiện shot chuyên dụng.

    Lớp cung cấp 2 cách dùng:
      - ``sample_video()``: quét toàn bộ video rồi trả về (như trước đây).
      - ``start_scan()`` / ``feed()`` / ``finish_scan()``: quét từng frame để
        pipeline streaming có thể dừng giữa chừng mà không cần decode hết video.
    """

    def __init__(
        self,
        delta_t=0.5,
        z_threshold=3.0,
        window_size=15,
        shot_distance_threshold=0.45,
    ):
        self.delta_t = float(delta_t)
        self.z_threshold = float(z_threshold)
        self.window_size = max(2, int(window_size))
        self.shot_distance_threshold = float(shot_distance_threshold)
        self._fps = 25.0
        self._reset_scan_state()
        logger.info(
            "Khởi tạo HSV/Bhattacharyya sampler (delta_t=%ss, z_threshold=%s, window=%s)",
            self.delta_t, self.z_threshold, self.window_size,
        )

    @staticmethod
    def _histogram(frame):
        """Compute a normalized HSV hue-saturation histogram for one frame."""
        small = cv2.resize(frame, (64, 64), interpolation=cv2.INTER_AREA)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
        hist = hist.astype(np.float32)
        hist /= float(hist.sum()) + 1e-7
        return hist

    @staticmethod
    def _bhattacharyya(hist_a, hist_b):
        """Convert histogram overlap into a bounded distance."""
        coefficient = float(np.sum(np.sqrt(hist_a * hist_b)))
        return float(np.sqrt(max(0.0, 1.0 - min(1.0, coefficient))))

    @staticmethod
    def _build_shots(cut_indices, fps, total_frames):
        starts = [0] + sorted(i for i in cut_indices if 0 < i < total_frames)
        starts = list(dict.fromkeys(starts))
        shots = []
        for shot_id, start in enumerate(starts):
            end_exclusive = starts[shot_id + 1] if shot_id + 1 < len(starts) else total_frames
            shots.append({
                "shot_id": shot_id,
                "start_sec": round(start / fps, 3) if fps > 0 else 0.0,
                "end_sec": round(end_exclusive / fps, 3) if fps > 0 else 0.0,
                "duration_sec": round((end_exclusive - start) / fps, 3) if fps > 0 else 0.0,
                "start_frame": start,
                "end_frame": max(start, end_exclusive - 1),
            })
        return shots or [{
            "shot_id": 0, "start_sec": 0.0,
            "end_sec": round(total_frames / fps, 3) if fps > 0 else 0.0,
            "duration_sec": round(total_frames / fps, 3) if fps > 0 else 0.0,
            "start_frame": 0, "end_frame": max(0, total_frames - 1),
        }]

    @staticmethod
    def _find_shot(frame_idx, shots):
        for shot in shots:
            if shot["start_frame"] <= frame_idx <= shot["end_frame"]:
                return shot
        return shots[-1]

    # ------------------------------------------------------------------
    # API quét từng frame (dùng cho pipeline streaming)
    # ------------------------------------------------------------------
    def _reset_scan_state(self):
        self._previous_hist = None
        self._recent_distances = []
        self._cut_indices = []
        self._last_selected_idx = -10**12
        self._frame_idx = 0
        self._selected_count = 0
        self._flash_candidate_count = 0

    @property
    def frame_index(self):
        """Index của frame kế tiếp sẽ được ``feed()`` xử lý."""
        return self._frame_idx

    def start_scan(self, fps):
        """Đặt lại trạng thái quét cho một video mới."""
        self._reset_scan_state()
        self._fps = float(fps) if fps and fps > 0 else 25.0

    def feed(self, frame, image_path=None):
        """
        Xử lý một frame vừa decode: tính histogram HSV, khoảng cách Bhattacharyya
        và Z-score, rồi quyết định giữ frame hay bỏ. Trả về sample dict hoặc None.
        """
        fps = self._fps
        frame_idx = self._frame_idx

        hist = self._histogram(frame)
        distance = 0.0 if self._previous_hist is None else self._bhattacharyya(self._previous_hist, hist)
        self._previous_hist = hist

        if len(self._recent_distances) >= 2:
            mean = float(np.mean(self._recent_distances))
            std = float(np.std(self._recent_distances))
            z_score = (distance - mean) / (std + 1e-6)
        else:
            z_score = 0.0

        is_cut = frame_idx > 0 and distance >= self.shot_distance_threshold
        if is_cut:
            self._cut_indices.append(frame_idx)

        self._recent_distances.append(distance)
        if len(self._recent_distances) > self.window_size:
            self._recent_distances.pop(0)

        time_sec = frame_idx / fps
        is_flash = z_score > self.z_threshold
        is_sample = (
            frame_idx == 0
            or (frame_idx - self._last_selected_idx) / fps >= self.delta_t
            or is_flash
            or is_cut
        )

        # Index luôn tăng để vòng lặp chính biết đã decode tới đâu.
        self._frame_idx += 1

        if not is_sample:
            return None

        self._last_selected_idx = frame_idx
        self._selected_count += 1
        if is_flash:
            self._flash_candidate_count += 1

        if image_path:
            cv2.imwrite(image_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

        return {
            "sample_id": self._selected_count,
            "frame_index": frame_idx,
            "time_sec": round(time_sec, 4),
            "is_iframe": False,
            "is_flash_candidate": bool(is_flash),
            "is_hsv_cut_candidate": bool(is_cut),
            "z_flash": round(float(z_score), 4),
            "d_bhattacharyya": round(float(distance), 4),
            "shot_id": len([i for i in self._cut_indices if i <= frame_idx]),
            "start_shot": None,
            "end_shot": None,
            "image_path": image_path,
            "frame_data": frame,
        }

    def finish_scan(self, samples, total_frames):
        """
        Đóng phiên quét: dựng danh sách shot và gán lại start/end_shot cho
        các sample. ``total_frames`` là số frame dùng làm mốc đóng shot cuối
        (số frame đã decode nếu quét hết video).
        """
        shots = self._build_shots(self._cut_indices, self._fps, total_frames)
        for sample in samples:
            shot = self._find_shot(sample["frame_index"], shots)
            sample["shot_id"] = shot["shot_id"]
            sample["start_shot"] = shot["start_sec"]
            sample["end_shot"] = shot["end_sec"]
        return shots

    def scan_stats(self, video_path, total_frames, decoded_frames, scan_complete, shots):
        """Tổng hợp metadata của video sau khi quét (thêm 2 trường so với bản cũ)."""
        fps = self._fps
        duration = total_frames / fps if fps > 0 else 0.0
        return {
            "video_path": str(video_path),
            "total_frames": total_frames,
            "fps": fps,
            "duration_sec": duration,
            "selected_frames": self._selected_count,
            "flash_candidates": self._flash_candidate_count,
            "shots": shots,
            "decoded_frames": decoded_frames,
            "scan_complete": bool(scan_complete),
        }

    # ------------------------------------------------------------------
    # API quét toàn video (giữ nguyên hành vi cũ)
    # ------------------------------------------------------------------
    def sample_video(self, video_path, output_dir=None, save_to_disk=False):
        "Decode a video and return sampled frames, shot metadata, and summary data."
        video_path = Path(video_path)
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Không mở được video: {video_path}")

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        total_hint = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if fps <= 0:
            fps = 25.0

        self.start_scan(fps)

        samples = []
        if save_to_disk and output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break

            image_path = None
            if save_to_disk and output_dir:
                image_path = str(
                    Path(output_dir) / f"frame_{self._frame_idx:06d}_{self._frame_idx / fps:.2f}s.jpg"
                )

            sample = self.feed(frame, image_path=image_path)
            if sample is not None:
                samples.append(sample)

        cap.release()

        total_frames = self._frame_idx
        shots = self.finish_scan(samples, total_frames=total_frames)

        selected = len(samples)
        logger.info(
            "HSV/Bhattacharyya sampling: %s/%s frames selected (%.1f%% reduction)",
            selected, total_frames,
            (100.0 * (total_frames - selected) / total_frames) if total_frames else 0.0,
        )
        video_info = self.scan_stats(
            video_path=video_path,
            total_frames=total_frames or total_hint,
            decoded_frames=total_frames,
            scan_complete=True,
            shots=shots,
        )
        return samples, shots, video_info
