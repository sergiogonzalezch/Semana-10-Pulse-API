"""La red de seguridad: un error que nadie manejó se vuelve un 500 en JSON, con el request id."""

import logging
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.config import settings
from app.middleware.request_logging import request_id_var

logger = logging.getLogger("pulse_api.errors")


async def error_handling_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Los errores de dominio ya los tradujo el handler; aquí solo llega lo inesperado."""
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception(
            "unhandled %s on %s %s", type(exc).__name__, request.method, request.url.path
        )
        body = {
            "detail": "Error interno del servidor",
            "error_code": "INTERNAL_ERROR",
            "status_code": 500,
            "request_id": request_id_var.get(),
        }
        if settings.app_env == "development":
            body["debug"] = {"exception": type(exc).__name__, "message": str(exc)}
        return JSONResponse(status_code=500, content=body)
