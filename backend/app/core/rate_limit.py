import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import settings

# Simple in-memory fixed-window limiter. Good enough for a single-process MVP;
# swap for a Redis-backed limiter (e.g. slowapi + redis) before running multiple
# backend replicas, since this state is per-process and resets on restart.
_attempts: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(key: str, max_attempts: int, window_seconds: int) -> None:
    now = time.monotonic()
    bucket = _attempts[key]
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()
    if len(bucket) >= max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts, please try again later.",
        )
    bucket.append(now)


def login_rate_limit(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    rate_limit(
        f"login:{client_host}",
        max_attempts=settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
        window_seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )
