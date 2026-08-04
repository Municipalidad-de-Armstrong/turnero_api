import time
from collections import defaultdict
from fastapi import HTTPException, Request, status

_request_history: dict[str, list[float]] = defaultdict(list)


class RateLimiter:
    """Rate limiter dependency using a sliding window per IP and route."""

    def __init__(self, max_requests: int = 15, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "127.0.0.1"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        key = f"{request.url.path}:{client_ip}"
        now = time.time()
        window_start = now - self.window_seconds

        timestamps = [t for t in _request_history[key] if t > window_start]
        _request_history[key] = timestamps

        if len(timestamps) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiadas solicitudes desde esta dirección IP. Intente nuevamente en unos minutos.",
            )

        _request_history[key].append(now)
