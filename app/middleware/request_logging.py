"""El id del request en cada línea de log, y los headers de tracing."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from fastapi import Request, Response

logger = logging.getLogger("pulse_api")

# Un valor por contexto: cada request ve el suyo, y las background tasks lo heredan.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Agrega el request id a cada línea de log, sin pasarlo como argumento."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def level_for(status_code: int) -> int:
    if status_code >= 500:
        return logging.ERROR
    if status_code >= 400:
        return logging.WARNING
    return logging.INFO


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:8]
    request.state.request_id = request_id
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
        logger.log(
            level_for(response.status_code),
            "method=%s path=%s status=%s duration_ms=%.2f",
            request.method, request.url.path, response.status_code, duration_ms,
        )
        return response
    finally:
        request_id_var.reset(token)
