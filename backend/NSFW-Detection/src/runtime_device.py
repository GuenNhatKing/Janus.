"""Thiết lập thiết bị chạy thống nhất cho PyTorch (ResNet) và TensorFlow (MobileNet).

Biến môi trường PROJ6_DEVICE:
  auto (mặc định): dùng GPU nếu backend nhận diện được, nếu không thì dùng CPU.
  cuda/gpu: yêu cầu GPU; phát sinh lỗi rõ ràng nếu backend không nhận diện được GPU.
  cpu: ép backend chạy CPU.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def requested_device() -> str:
    value = os.environ.get("PROJ6_DEVICE", "auto").strip().lower()
    aliases = {"gpu": "cuda", "nvidia": "cuda", "automatic": "auto"}
    value = aliases.get(value, value)
    if value not in {"auto", "cpu", "cuda"}:
        raise ValueError(
            f"PROJ6_DEVICE={value!r} không hợp lệ. Chọn 'auto', 'cpu' hoặc 'cuda'."
        )
    return value


def get_torch_device(torch_module=None):
    """Trả về torch.device theo PROJ6_DEVICE; không âm thầm fallback khi yêu cầu CUDA."""
    if torch_module is None:
        import torch as torch_module

    setting = requested_device()
    has_cuda = bool(torch_module.cuda.is_available())
    if setting == "cpu":
        return torch_module.device("cpu")
    if setting == "cuda":
        if not has_cuda:
            raise RuntimeError(
                "PROJ6_DEVICE=cuda nhưng PyTorch không nhận diện GPU CUDA. "
                "Hãy kiểm tra GPU/driver và cài bản PyTorch có CUDA; chạy python -c "
                "\"import torch; print(torch.cuda.is_available(), torch.version.cuda)\"."
            )
        return torch_module.device("cuda:0")
    return torch_module.device("cuda:0" if has_cuda else "cpu")


def configure_tensorflow(tf_module):
    """Cấu hình TensorFlow; bật memory growth để tránh chiếm toàn bộ VRAM ngay khi khởi động."""
    setting = requested_device()
    physical_gpus = tf_module.config.list_physical_devices("GPU")

    if setting == "cpu":
        try:
            tf_module.config.set_visible_devices([], "GPU")
        except RuntimeError as exc:
            raise RuntimeError(
                "Không thể chuyển TensorFlow sang CPU vì runtime đã khởi tạo trước đó. "
                "Hãy đặt PROJ6_DEVICE=cpu trước khi chạy chương trình."
            ) from exc
        logger.info("TensorFlow device: CPU (theo PROJ6_DEVICE=cpu)")
        return "CPU"

    if setting == "cuda" and not physical_gpus:
        raise RuntimeError(
            "PROJ6_DEVICE=cuda nhưng TensorFlow không nhận diện GPU. Trên Linux/WSL2, "
            "kiểm tra nvidia-smi và cài TensorFlow GPU cùng CUDA/cuDNN tương thích. "
            "Kiểm tra bằng: python -c \"import tensorflow as tf; "
            "print(tf.config.list_physical_devices('GPU'))\"."
        )

    for gpu in physical_gpus:
        try:
            tf_module.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError as exc:
            logger.warning("Không bật được memory growth cho %s: %s", gpu, exc)

    visible_gpus = tf_module.config.get_visible_devices("GPU")
    if visible_gpus:
        labels = ", ".join(getattr(gpu, "name", str(gpu)) for gpu in visible_gpus)
        logger.info("TensorFlow device: GPU (%s); memory growth bật", labels)
        return "GPU"

    logger.info("TensorFlow device: CPU (GPU không khả dụng; PROJ6_DEVICE=%s)", setting)
    return "CPU"


def get_tensorflow_device_name(tf_module) -> str:
    """Nhãn thiết bị TensorFlow hiện đang được phép sử dụng."""
    try:
        visible = tf_module.config.get_visible_devices("GPU")
    except Exception:
        visible = tf_module.config.list_physical_devices("GPU")
    return "GPU" if visible else "CPU"


def get_torch_device_name(torch_module=None) -> str:
    """Return a readable CPU or GPU label for the selected PyTorch device."""
    if torch_module is None:
        import torch as torch_module
    device = get_torch_device(torch_module)
    if device.type == "cuda":
        try:
            name = torch_module.cuda.get_device_name(device)
            return f"GPU ({name})"
        except Exception:
            return "GPU (CUDA)"
    return "CPU"


def get_runtime_device_summary() -> str:
    """Tóm tắt thiết bị backend đã được nạp, phù hợp lưu kèm JSON benchmark."""
    import sys

    parts = [f"requested={requested_device()}"]
    torch_module = sys.modules.get("torch")
    if torch_module is not None:
        try:
            parts.append(f"PyTorch={get_torch_device_name(torch_module)}")
        except Exception as exc:
            parts.append(f"PyTorch=unavailable ({exc})")

    tf_module = sys.modules.get("tensorflow")
    if tf_module is not None:
        try:
            parts.append(f"TensorFlow={get_tensorflow_device_name(tf_module)}")
        except Exception as exc:
            parts.append(f"TensorFlow=unavailable ({exc})")

    return "; ".join(parts)
