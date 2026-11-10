"""설치본(pythonw)에서도 남는 파일 로그. %USERPROFILE%\\.posture_app\\logs"""
from __future__ import annotations

import logging
import os
import traceback
from logging.handlers import RotatingFileHandler
from typing import Optional

from config import DATA_DIR

LOG_DIR = os.path.join(DATA_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger
    log = logging.getLogger("posture_app")
    log.setLevel(logging.INFO)
    log.propagate = False
    if not log.handlers:
        handler = RotatingFileHandler(
            LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        log.addHandler(handler)
    _logger = log
    return log


def info(scope: str, message: str, **extra) -> None:
    parts = [f"[{scope}] {message}"]
    for k, v in extra.items():
        parts.append(f"{k}={v}")
    get_logger().info(" ".join(parts))


def error(scope: str, message: str, **extra) -> None:
    parts = [f"[{scope}] {message}"]
    for k, v in extra.items():
        parts.append(f"{k}={v}")
    get_logger().error(" ".join(parts))


def exception(scope: str, message: str, exc: BaseException | None = None) -> None:
    tb = traceback.format_exc() if exc is None else "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )
    get_logger().error("[%s] %s\n%s", scope, message, tb)
