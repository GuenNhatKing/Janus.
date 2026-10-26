import json
import logging
import os

import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
from runtime_device import get_torch_device

logger = logging.getLogger(__name__)


class Bottleneck(nn.Module):
    """Residual bottleneck block used by the convolutional classifier."""
    expansion = 4

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super().__init__()
        self.conv1 = nn.Conv2d(inplanes, planes, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv3 = nn.Conv2d(planes, planes * self.expansion, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(planes * self.expansion)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample

    def forward(self, x):
        identity = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity
        return self.relu(out)


def _make_layer(inplanes, planes, blocks, stride=1):
    """Build one residual stage and return it with its output channel count."""
    downsample = None
    if stride != 1 or inplanes != planes * Bottleneck.expansion:
        downsample = nn.Sequential(
            nn.Conv2d(inplanes, planes * Bottleneck.expansion, kernel_size=1, stride=stride, bias=False),
            nn.BatchNorm2d(planes * Bottleneck.expansion),
        )
    layers = [Bottleneck(inplanes, planes, stride, downsample)]
    inplanes = planes * Bottleneck.expansion
    for _ in range(1, blocks):
        layers.append(Bottleneck(inplanes, planes))
    return nn.Sequential(*layers), inplanes


class ResNet50FCN(nn.Module):
    """ResNet-50 backbone with a 1x1 classifier and global average pooling."""

    def __init__(self, num_classes):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        self.layer1, inplanes = _make_layer(64, 64, 3)
        self.layer2, inplanes = _make_layer(inplanes, 128, 4, stride=2)
        self.layer3, inplanes = _make_layer(inplanes, 256, 6, stride=2)
        self.layer4, inplanes = _make_layer(inplanes, 512, 3, stride=2)

        self.classifier = nn.Conv2d(
            in_channels=2048,
            out_channels=num_classes,
            kernel_size=1,
            stride=1,
            padding=0
        )

    def forward(self, x):
        """Return class logits for a batch of image tensors."""
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.classifier(x)

        x = F.adaptive_avg_pool2d(x, output_size=1)
        x = torch.flatten(x, start_dim=1)
        return x


# ResNet Classifier
class ResNetClassifier:

    def __init__(
        self,
        model_path,
        batch_size=21,
        device=None
    ):
        self.device = get_torch_device(torch) if device is None else torch.device(device)
        if self.device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                f"Thiết bị {self.device} được yêu cầu nhưng PyTorch không khả dụng CUDA. "
                "Kiểm tra driver NVIDIA và cài PyTorch bản CUDA."
            )
        self.batch_size = batch_size
        self.model_path = model_path

        # Tối ưu hóa số luồng CPU: giải quyết triệt để lỗi thiếu torch.set_num_threads()
        if self.device.type == "cpu":
            optimal_threads = min(4, os.cpu_count() or 4)
            torch.set_num_threads(optimal_threads)
            logger.info(f"Tối ưu CPU inference: Thiết lập torch.set_num_threads({optimal_threads})")

        # ImageNet normalization
        self.imagenet_mean = torch.tensor(
            [0.485, 0.456, 0.406], dtype=torch.float32
        ).view(3, 1, 1)

        self.imagenet_std = torch.tensor(
            [0.229, 0.224, 0.225], dtype=torch.float32
        ).view(3, 1, 1)

        # Định nghĩa 3 kích thước chuẩn tương ứng với 3 loại tỉ lệ cho phép:
        self.target_configs = {
            "portrait": {
                "ratio": 9 / 16,            # 9:16 (0.5625)
                "target_size": (360, 640),  # (Width, Height) -> Grid: 20x12 = 240 vùng đặc trưng
            },
            "square": {
                "ratio": 1.0,               # 1:1 (1.0000)
                "target_size": (480, 480),  # (Width, Height) -> Grid: 15x15 = 225 vùng đặc trưng
            },
            "landscape": {
                "ratio": 16 / 9,            # 16:9 (1.7778)
                "target_size": (640, 360),  # (Width, Height) -> Grid: 12x20 = 240 vùng đặc trưng
            },
        }
        self.aspect_ratio_tolerance = 0.08

        logger.info(f"Khởi tạo ResNet-50-FCN trên {self.device} | Hỗ trợ 3 tỉ lệ chuẩn: 16:9 (640x360), 9:16 (360x640), 1:1 (480x480)")

        self._load_model()

    def _load_model(self):
        logger.info(f"Đang tải checkpoint từ {self.model_path}...")
        checkpoint = torch.load(self.model_path, map_location="cpu")

        self.classes = checkpoint["classes"]
        self.class_to_idx = checkpoint["class_to_idx"]
        self.adult_idx = self.class_to_idx["adult"]
        num_classes = len(self.classes)

        self.model = ResNet50FCN(num_classes=num_classes)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model = self.model.to(self.device)
        self.model.eval()

        logger.info(f"Load model thành công trên {self.device}. Classes: {self.classes}")

    def determine_target_config(self, orig_w, orig_h):
        """
        Xác định cấu hình kích thước đích dựa trên tỉ lệ ảnh gốc.
        Chỉ chấp nhận 3 loại tỉ lệ: 16:9, 9:16, hoặc 1:1.
        """
        if orig_w <= 0 or orig_h <= 0:
            raise ValueError(f"Kích thước không hợp lệ: {orig_w}x{orig_h}")

        current_ratio = orig_w / orig_h
        best_name = None
        best_error = float("inf")

        for name, config in self.target_configs.items():
            error = abs(current_ratio - config["ratio"])
            if error < best_error:
                best_error = error
                best_name = name

        if best_error > self.aspect_ratio_tolerance:
            raise ValueError(
                f"Aspect ratio không hợp lệ: {orig_w}x{orig_h} (ratio={current_ratio:.4f}). "
                f"Chỉ chấp nhận 3 loại tỉ lệ: 16:9, 9:16, hoặc 1:1."
            )

        return best_name, self.target_configs[best_name]["target_size"]

    def _get_frame_bgr(self, sample):
        frame_bgr = sample.get("frame_data")
        if frame_bgr is None:
            image_path = sample.get("image_path")
            if image_path is None or not os.path.exists(image_path):
                raise FileNotFoundError(f"Không tìm thấy image: {image_path}")
            frame_bgr = cv2.imread(image_path)

        if frame_bgr is None:
            raise ValueError("Không thể đọc frame.")
        return frame_bgr

    def crop_center(self, frame_bgr, target_w, target_h):
        """
        Resize toàn bộ frame về kích thước target tương ứng của từng tỉ lệ:
        - 16:9: 640x360
        - 9:16: 360x640
        - 1:1: 480x480

        Không cắt bỏ vùng trung tâm. Tên hàm được giữ lại để tương thích với
        các caller hiện có trong proposed.
        """
        orig_h, orig_w = frame_bgr.shape[:2]
        if (orig_w, orig_h) == (target_w, target_h):
            return frame_bgr

        interpolation = (
            cv2.INTER_AREA
            if orig_w > target_w and orig_h > target_h
            else cv2.INTER_LINEAR
        )
        return cv2.resize(
            frame_bgr,
            (target_w, target_h),
            interpolation=interpolation
        )

    def crop_center_360x640(self, frame_bgr):
        """Resize the frame to the configured size from its aspect ratio."""
        orig_h, orig_w = frame_bgr.shape[:2]
        _, (target_w, target_h) = self.determine_target_config(orig_w, orig_h)
        return self.crop_center(frame_bgr, target_w, target_h)

    def _preprocess_frame(self, frame_bgr, is_center_crop=False):
        """
        Chuẩn hóa frame đưa vào ResNet-50 FCN theo đúng tỉ lệ (16:9, 9:16, 1:1):
        - Mặc định: resize về target size (640x360, 360x640, hoặc 480x480)
        - Nếu is_center_crop=True: resize toàn bộ frame về kích thước tương ứng
        """
        orig_h, orig_w = frame_bgr.shape[:2]
        ratio_type, (target_w, target_h) = self.determine_target_config(orig_w, orig_h)

        if is_center_crop:
            img = self.crop_center(frame_bgr, target_w, target_h)
        else:
            if (orig_w, orig_h) != (target_w, target_h):
                interp = cv2.INTER_AREA if (orig_w > target_w and orig_h > target_h) else cv2.INTER_LINEAR
                img = cv2.resize(frame_bgr, (target_w, target_h), interpolation=interp)
            else:
                img = frame_bgr

        # BGR -> RGB
        frame_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Chuẩn hóa Tensor [0, 1] và trừ ImageNet mean/std
        tensor = torch.from_numpy(frame_rgb).permute(2, 0, 1).float() / 255.0
        tensor = (tensor - self.imagenet_mean) / self.imagenet_std

        return tensor, ratio_type, orig_w, orig_h, target_w, target_h

    def _predict_batch(self, tensors):
        if not tensors:
            return torch.empty((0, len(self.classes)), device=self.device)

        # Kiểm tra nếu tất cả tensors cùng kích thước
        first_shape = tensors[0].shape
        if all(t.shape == first_shape for t in tensors):
            batch = torch.stack(tensors, dim=0).to(self.device, non_blocking=True)
            with torch.inference_mode():
                logits = self.model(batch)
                probabilities = torch.softmax(logits, dim=1)
            return probabilities

        # Nếu batch chứa nhiều tỉ lệ/kích thước khác nhau: gom nhóm theo shape để chạy batch inference
        shape_groups = {}
        for idx, t in enumerate(tensors):
            s = tuple(t.shape)
            shape_groups.setdefault(s, []).append((idx, t))

        results = [None] * len(tensors)
        for s, group in shape_groups.items():
            indices, group_tensors = zip(*group)
            batch = torch.stack(list(group_tensors), dim=0).to(self.device, non_blocking=True)
            with torch.inference_mode():
                logits = self.model(batch)
                probs = torch.softmax(logits, dim=1)
            for idx, p in zip(indices, probs):
                results[idx] = p

        return torch.stack(results, dim=0)

    def predict_samples(
        self,
        samples,
        output_json_path=None,
        save_to_disk=True
    ):
        """Classify sampled frame records and optionally write their probabilities."""
        if not samples:
            return []

        logger.info(f"Bắt đầu tiền xử lí và inference {len(samples)} frames...")

        results = []
        for start in range(0, len(samples), self.batch_size):
            batch_samples = samples[start:start + self.batch_size]
            tensors = []
            meta_list = []
            for s in batch_samples:
                frame_bgr = self._get_frame_bgr(s)
                tensor, _, orig_w, orig_h, target_w, target_h = self._preprocess_frame(frame_bgr)
                tensors.append(tensor)
                meta_list.append((orig_w, orig_h, target_w, target_h))

            probabilities = self._predict_batch(tensors)

            for i, s in enumerate(batch_samples):
                probs = probabilities[i]
                predicted_idx = int(torch.argmax(probs).item())
                adult_probability = float(probs[self.adult_idx].item())
                orig_w, orig_h, target_w, target_h = meta_list[i]

                result = {
                    "frame_index": s.get("frame_index"),
                    "time_sec": s.get("time_sec"),
                    "image_path": s.get("image_path", "in_memory"),
                    "original_size": f"{orig_w}x{orig_h}",
                    "input_size": f"{target_w}x{target_h}",
                    "predicted_class": self.classes[predicted_idx],
                    "adult_probability": round(adult_probability, 6),
                }
                results.append(result)

        if save_to_disk and output_json_path:
            output_dir = os.path.dirname(output_json_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump({"results": results}, f, indent=2, ensure_ascii=False)

            logger.info(f"Đã lưu kết quả: {output_json_path}")

        logger.info(f"Hoàn thành inference: {len(results)} frames.")
        return results

    def predict_frame_batch(self, frames_bgr, is_center_crop=False):
        """
        Dự đoán xác suất Adult theo batch cho danh sách frame BGR.
        """
        if not frames_bgr:
            return []
        tensors = [self._preprocess_frame(f, is_center_crop=is_center_crop)[0] for f in frames_bgr]
        probs = self._predict_batch(tensors)
        return [float(p[self.adult_idx].item()) for p in probs]

    def warmup(self):
        """
        Run one dummy inference before processing real frames.
        """
        dummy = torch.zeros((1, 3, 360, 640), device=self.device)
        with torch.inference_mode():
            _ = self.model(dummy)
        logger.info("ResNet-50 FCN Warm-up pass hoàn tất trên RAM.")
