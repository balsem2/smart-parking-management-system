import os
import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException


MAX_ATTEMPTS = int(os.getenv("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "5"))
WINDOW_SECONDS = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "900"))
_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def _recent_attempts(key: str, now: float) -> list[float]:
    attempts = [attempt for attempt in _attempts[key] if now - attempt < WINDOW_SECONDS]
    _attempts[key] = attempts
    return attempts


def ensure_login_allowed(key: str) -> None:
    with _lock:
        if len(_recent_attempts(key, time.monotonic())) >= MAX_ATTEMPTS:
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")


def record_failed_login(key: str) -> None:
    with _lock:
        _recent_attempts(key, time.monotonic()).append(time.monotonic())


def clear_login_attempts(key: str) -> None:
    with _lock:
        _attempts.pop(key, None)
