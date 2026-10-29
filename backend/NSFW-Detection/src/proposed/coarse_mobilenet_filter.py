import os
import json
import logging
from pathlib import Path
import numpy as np
import cv2

# Thiết bị TensorFlow được cấu hình qua PROJ6_DEVICE=auto|cpu|cuda.
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import tensorflow as tf
tf.get_logger().setLevel("ERROR")
from runtime_device import configure_tensorflow, get_tensorflow_device_name
configure_tensorflow(tf)

logger = logging.getLogger(__name__)


class CoarseMobileNetFilter:
    """Score candidate frames with MobileNet and retain scores above a threshold."""

    def __init__(self, model_path, batch_size=32, rejection_threshold=0.35):
        self.model_path = str(Path(model_path).resolve())
        self.batch_size = batch_size
        self.rejection_threshold = rejection_threshold
        self.target_size = (224, 224)
        self.device_name = get_tensorflow_device_name(tf)

        logger.info(
            f"Khởi tạo CoarseMobileNetFilter trên {get_tensorflow_device_name(tf)} (Batch={self.batch_size}, "
            f"Threshold={self.rejection_threshold}, Input={self.target_size})"
        )
        self._load_model()

    def _load_model(self):
        logger.info(f"Đang tải MobileNetV3-Small ({get_tensorflow_device_name(tf)}) từ: {self.model_path}...")
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Không tìm thấy mô hình MobileNet: {self.model_path}")
        tf_device = "/GPU:0" if self.device_name == "GPU" else "/CPU:0"
        with tf.device(tf_device):
            self.model = tf.keras.models.load_model(self.model_path, compile=False)
        logger.info(f"Tải MobileNetV3-Small thành công trên {self.device_name}.")

    def warmup(self):
        """
        Run one dummy inference before processing real candidates.
        """
        dummy = np.zeros((1, 224, 224, 3), dtype=np.float32)
        _ = self.model.predict(dummy, verbose=0)
        logger.info(f"MobileNetV3-Small Warm-up pass hoàn tất; thiết bị: {get_tensorflow_device_name(tf)}.")

    def _preprocess_frame(self, frame_bgr):
        resized = cv2.resize(frame_bgr, self.target_size, interpolation=cv2.INTER_LINEAR)
        frame_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        image_array = (frame_rgb.astype(np.float32) / 127.5) - 1.0
        return image_array

    def score_samples(self, samples):
        """
        Dự đoán MỘT lô candidate frames và ghi p_mobile/p_normal/status vào
        chính từng sample. Trả về Anchor Set A (p_mobile >= rejection_threshold).

        Dùng được cho pipeline streaming: mỗi lô được suy luận ngay khi đủ
        ``batch_size`` mẫu thay vì chờ tích lũy hết video.
        """
        if not samples:
            return []

        batch_arrays = [self._preprocess_frame(s["frame_data"]) for s in samples]
        batch_input = np.array(batch_arrays, dtype=np.float32)

        probabilities = self.model.predict(batch_input, batch_size=self.batch_size, verbose=0)

        anchor_set = []
        for idx, sample in enumerate(samples):
            probs = probabilities[idx]
            p_mobile = float(probs[0])
            p_normal = float(probs[1]) if len(probs) > 1 else float(1.0 - p_mobile)

            is_early_rejected = bool(p_mobile < self.rejection_threshold)

            sample["p_mobile"] = round(p_mobile, 6)
            sample["p_normal"] = round(p_normal, 6)
            sample["status"] = "EARLY_REJECTED" if is_early_rejected else "ANCHOR_CANDIDATE"

            if not is_early_rejected:
                anchor_set.append(sample)

        return anchor_set

    @staticmethod
    def build_stage2_records(samples):
        """
        Dựng bản ghi kết quả Stage 2 theo đúng schema cũ (không kèm frame_data).
        Chỉ truyền các sample đã qua ``score_samples``.
        """
        records = []
        for sample in samples:
            records.append({
                "sample_id": sample["sample_id"],
                "frame_index": sample["frame_index"],
                "time_sec": sample["time_sec"],
                "is_iframe": sample["is_iframe"],
                "is_flash_candidate": sample["is_flash_candidate"],
                "z_flash": sample["z_flash"],
                "d_bhattacharyya": sample["d_bhattacharyya"],
                "shot_id": sample["shot_id"],
                "start_shot": sample["start_shot"],
                "end_shot": sample["end_shot"],
                "p_mobile": sample["p_mobile"],
                "p_normal": sample["p_normal"],
                "status": sample["status"],
                "image_path": sample.get("image_path"),
            })
        return records

    def filter_candidates(self, samples, output_json_path=None, save_to_disk=False):
        """
        Dự đoán hàng loạt các candidate frames từ Stage 1.
        Phân loại Early Rejection (p_mobile < 0.35) và gom Anchor Set A (p_mobile >= 0.35).
        """
        if not samples:
            logger.info("Stage 2: Không có candidate frame nào từ Stage 1.")
            return [], []

        logger.info(f"Stage 2: Bắt đầu quét thô {len(samples)} frames với MobileNetV3-Small ({get_tensorflow_device_name(tf)})...")

        anchor_set = self.score_samples(samples)
        all_results = self.build_stage2_records(samples)

        rejection_rate = (len(samples) - len(anchor_set)) / len(samples) * 100 if samples else 0.0
        logger.info(
            f"Stage 2 hoàn thành: Loại bỏ sớm {len(samples) - len(anchor_set)}/{len(samples)} frames ({rejection_rate:.1f}%). "
            f"Số tâm điểm nghi vấn (Anchors): {len(anchor_set)}."
        )

        if save_to_disk and output_json_path:
            out_p = Path(output_json_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                json.dump({
                    "total_candidates": len(samples),
                    "rejected_count": len(samples) - len(anchor_set),
                    "anchor_count": len(anchor_set),
                    "rejection_threshold": self.rejection_threshold,
                    "results": all_results
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"Đã lưu kết quả Stage 2: {output_json_path}")

        return all_results, anchor_set
