#!/usr/bin/env python3
"""Kiểm tra riêng GPU cho cả PyTorch/ResNet và TensorFlow/MobileNet.

Chạy từ thư mục src: python check_gpu.py
Để bắt buộc cả hai backend phải nhận GPU: PROJ6_DEVICE=cuda python check_gpu.py
"""
from __future__ import annotations

import os

from log_config import configure, get_logger

# Giữ nguyên log C++ của TensorFlow để còn chẩn đoán lỗi CUDA/cuDNN.
configure(native_stderr=False)
logger = get_logger(__name__)

import torch
from runtime_device import configure_tensorflow, get_torch_device, get_tensorflow_device_name


def main() -> int:
    """Run a small computation and one model inference on each backend."""
    torch_device = get_torch_device(torch)
    x = torch.randn((512, 512), device=torch_device)
    y = x @ x
    if torch_device.type == "cuda":
        torch.cuda.synchronize(torch_device)
    logger.info("[PyTorch/ResNet] device=%s; cuda_available=%s; torch_cuda=%s", y.device, torch.cuda.is_available(), torch.version.cuda)
    if torch_device.type == "cuda":
        logger.info("[PyTorch/ResNet] GPU=%s", torch.cuda.get_device_name(torch_device))

    # Import TensorFlow after PyTorch so the check uses the same load order as the pipeline.
    try:
        import tensorflow as tf
    except ImportError as exc:
        logger.error("Chưa cài TensorFlow. Với môi trường GPU Linux/WSL2, cài src/requirements-gpu.txt trước.")
        logger.error("Chi tiết: %s", exc)
        return 3
    configure_tensorflow(tf)
    tf_device_name = get_tensorflow_device_name(tf)
    tf_device = "/GPU:0" if tf_device_name == "GPU" else "/CPU:0"
    with tf.device(tf_device):
        a = tf.random.normal((512, 512))
        b = tf.matmul(a, a)
    _ = b.numpy()  # Force completion, so the check verifies real execution.
    logger.info("[TensorFlow/MobileNet] matrix_device=%s; physical_gpus=%s", b.device, tf.config.list_physical_devices("GPU"))

    # Load the configured model as well as running the backend matrix operation.
    from env_config import get_env
    model_path = get_env("MOBILENET_MODEL", "models/mobilenetv3_small_adult_normal.keras", resolve=True)
    try:
        with tf.device(tf_device):
            model = tf.keras.models.load_model(model_path, compile=False)
            prediction = model(tf.zeros((1, 224, 224, 3), dtype=tf.float32), training=False)
            _ = prediction.numpy()
        logger.info("[TensorFlow/MobileNet] model_loaded=%s; output_shape=%s; output_device=%s", model_path, tuple(prediction.shape), prediction.device)
    except Exception as exc:
        logger.error("TensorFlow/Keras không nạp hoặc chạy được mô hình MobileNet: %s", model_path)
        logger.error("Chi tiết: %s: %s", type(exc).__name__, exc)
        logger.error("Hãy kiểm tra TensorFlow 2.20.0 và Keras 3.13.2 đã được cài trong đúng .venv.")
        return 4

    requested = os.environ.get("PROJ6_DEVICE", "auto").strip().lower()
    if requested in {"cuda", "gpu", "nvidia"} and (torch_device.type != "cuda" or tf_device_name != "GPU"):
        logger.error("PROJ6_DEVICE=cuda yêu cầu cả PyTorch và TensorFlow đều dùng GPU.")
        return 2
    if torch_device.type != "cuda" or tf_device_name != "GPU":
        logger.warning("Ít nhất một backend đang dùng CPU. Muốn cả hai bắt buộc dùng GPU, chạy PROJ6_DEVICE=cuda python check_gpu.py.")
        return 1
    logger.info("OK: PyTorch (ResNet) và TensorFlow/Keras (MobileNet) đều nhận GPU; mô hình MobileNet thực tế đã được nạp và chạy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
