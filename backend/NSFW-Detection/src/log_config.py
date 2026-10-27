"""Cấu hình logging tập trung cho toàn bộ PROJ-6 (benchmark + pipeline).

Mọi entrypoint gọi ``configure()`` sau khi đưa ``src/`` vào ``sys.path`` và
TRƯỚC khi import TensorFlow/PyTorch:

    from log_config import configure, get_logger
    configure()
    logger = get_logger(__name__)

Làm gì:

- Ghi log bằng ``logging`` thay cho ``print``: mỗi record được handler flush
  ngay khi phát sinh, ghi đồng thời ra console lẫn file. Console bị chặn
  (pipe đầy) không còn làm mất log vì bản ghi đã nằm trên đĩa.
- Tắt warning của Python lẫn của thư viện (TensorFlow/absl, matplotlib, PIL,
  urllib3, skimage...).
- Chặn log C++ của thư viện ghi thẳng vào stderr (fd 2). ``sys.stderr`` của
  Python được tách ra trước khi chặn nên traceback và log Python vẫn hiển thị
  bình thường. Đặt ``PROJ6_NATIVE_STDERR=1`` nếu muốn xem lại log gốc C++.

Cấu hình qua môi trường:

- ``PROJ6_LOG_LEVEL``: DEBUG/INFO/WARNING/ERROR (mặc định INFO).
- ``PROJ6_LOG_FILE``: đường dẫn file log dùng chung cho mọi tiến trình con.
"""

from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(message)s"
LOG_DATEFMT = "%H:%M:%S"

# Thư viện ồn ào: nâng lên ERROR để chỉ còn lỗi thật.
_NOISY_LOGGERS = {
    "tensorflow": logging.ERROR,
    "absl": logging.ERROR,
    "matplotlib": logging.ERROR,
    "matplotlib.font_manager": logging.ERROR,
    "PIL": logging.ERROR,
    "urllib3": logging.ERROR,
    "asyncio": logging.ERROR,
    "numba": logging.ERROR,
}

# Chỉ chặn một lần cho mỗi tiến trình.
_native_stderr_blocked = False


def _block_native_stderr() -> None:
    """Chặn log C++ (fd 2) nhưng giữ ``sys.stderr`` của Python."""
    global _native_stderr_blocked
    if _native_stderr_blocked or os.environ.get("PROJ6_NATIVE_STDERR") == "1":
        return
    try:
        sys.stderr.flush()
        original_fd = os.dup(2)
        # sys.stderr trỏ tới bản sao fd cũ: Python vẫn ghi ra terminal/log.
        sys.stderr = os.fdopen(os.dup(original_fd), "w")
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, 2)
        os.close(devnull_fd)
        _native_stderr_blocked = True
    except OSError:
        # Không chặn được thì cứ để nguyên, không được làm hỏng tiến trình.
        _native_stderr_blocked = True


def configure(level=None, log_file=None, console=True, native_stderr=True) -> logging.Logger:
    """Cấu hình logging cho tiến trình hiện tại; idempotent (gọi lại được)."""
    # Cảnh báo của TensorFlow/absl phải được đặt TRƯỚC khi import TF.
    # Muốn giữ log gốc của thư viện thì đặt PROJ6_NATIVE_STDERR=1.
    if os.environ.get("PROJ6_NATIVE_STDERR") != "1":
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
        os.environ["ABSL_MIN_LOG_LEVEL"] = "2"
        os.environ["GLOG_minloglevel"] = "2"

    # Bỏ toàn bộ warning của Python và của thư viện bên thứ ba.
    warnings.filterwarnings("ignore")

    level_name = str(level or os.environ.get("PROJ6_LOG_LEVEL", "INFO")).upper()
    level_value = getattr(logging, level_name, logging.INFO)

    if log_file is None:
        log_file = os.environ.get("PROJ6_LOG_FILE")

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATEFMT)

    root = logging.getLogger()
    root.setLevel(level_value)
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    if console:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    for name, noisy_level in _NOISY_LOGGERS.items():
        logging.getLogger(name).setLevel(noisy_level)

    if native_stderr:
        _block_native_stderr()

    return root


def get_logger(name=None) -> logging.Logger:
    """Lấy logger theo tên module (mặc định là logger root)."""
    return logging.getLogger(name)