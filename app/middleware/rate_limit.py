"""Rate limiting en memoria: cuántos requests por minuto acepta la API de cada IP."""

import logging
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.config import settings

logger = logging.getLogger("pulse_api.rate_limit")

# El login tiene su propio límite, más estricto: es la puerta de la fuerza bruta.
LOGIN_PATH = "/api/v1/auth/login"
WINDOW_SECONDS = 60.0


class SlidingWindowLimiter:
    """Ventana deslizante por llave, en la memoria de este proceso."""

    def __init__(self) -> None:
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int) -> tuple[bool, int, int]:
        now = time.monotonic()
        hits = self.hits[key]
        while hits and hits[0] <= now - WINDOW_SECONDS:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = int(hits[0] + WINDOW_SECONDS - now) + 1
            return False, 0, retry_after
        hits.append(now)
        return True, limit - len(hits), 0


limiter = SlidingWindowLimiter()


async def rate_limit_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.method == "OPTIONS":
        return await call_next(request)

    ip = request.client.host if request.client else "unknown"
    checks = [(f"ip:{ip}", settings.rate_limit_per_minute)]
    if request.method == "POST" and request.url.path == LOGIN_PATH:
        checks.insert(0, (f"login:{ip}", settings.login_rate_limit_per_minute))

    for key, limit in checks:
        allowed, remaining, retry_after = limiter.hit(key, limit)
        if not allowed:
            logger.warning("rate limit exceeded for %s (%d per minute)", key, limit)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Demasiados requests: el límite es {limit} por minuto",
                    "error_code": "RATE_LIMITED",
                    "status_code": 429,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response
