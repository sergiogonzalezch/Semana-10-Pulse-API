"""app/main.py
Punto de entrada: app FastAPI, CORS, handlers de error, health check y routers.
"""
from __future__ import annotations

# logging para el log
import logging
# os revisa permisos de escritura; time mide el uptime
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
# El engine, la sesión por request y la revisión de la base
from app.database import check_database, engine, get_db
from app.exceptions import PulseError, UNIQUE_CONSTRAINTS
# Los tres middleware: errores, rate limiting y tracing (con su filtro de log)
from app.middleware.errors import error_handling_middleware
from app.middleware.rate_limit import rate_limit_middleware
from app.middleware.request_logging import RequestIdFilter, request_id_var, request_logging_middleware
# El manager de WebSockets, para contar las conexiones abiertas
from app.realtime import manager
# El router de la versión 1, con todos los routers adentro
from app.api import api_router

# El formato del log: nivel, logger, el id del request entre corchetes y el mensaje
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s [%(request_id)s] %(message)s",
)
# El filtro va en el handler: así TODA línea que llega a él trae su request_id
for handler in logging.getLogger().handlers:
    handler.addFilter(RequestIdFilter())

# El logger de la app (el mismo nombre que usa el middleware)
logger = logging.getLogger("pulse_api")


tags_metadata = [
    {"name": "auth", "description": "Registro, login, refresh y logout."},
    {"name": "users", "description": "Perfiles y administración de usuarios."},
    {"name": "categories", "description": "Categorías del blog."},
    {"name": "posts", "description": "Posts, borradores, búsqueda y publicación."},
    {"name": "comments", "description": "Comentarios de posts."},
    {"name": "notifications", "description": "Notificaciones persistentes del usuario."},
    {"name": "realtime", "description": "Canal WebSocket y cliente de prueba."},
    {"name": "health", "description": "Estado del servicio y de la base de datos."},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # --- Arranque. Si algo falla aquí, uvicorn no acepta ni un request ---
    # 1. La base contesta (si no, RuntimeError y "Application startup failed")
    version = await check_database()
    logger.info("database connected: %s", version)
    # 2. Las carpetas de var/ existen y se puede escribir en ellas
    folders = [settings.upload_dir, settings.outbox_path.parent, settings.analytics_path.parent]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
        # Existe pero es de otro usuario o de solo lectura: mejor saberlo ahora
        if not os.access(folder, os.W_OK):
            raise RuntimeError(f"No se puede escribir en {folder}")
    logger.info("folders ready: %s", ", ".join(sorted({str(f) for f in folders})))
    # 3. Cuándo arrancó: el health check calcula el uptime
    app.state.started_at = time.monotonic()
    # --- La app atiende requests mientras está aquí ---
    yield
    # --- Apagado: uvicorn ya dejó de aceptar requests y cerró los WebSockets ---
    uptime = time.monotonic() - app.state.started_at
    logger.info("shutting down after %.1fs; open websockets: %d", uptime, manager.count())
    # Cerrar las conexiones del pool: PostgreSQL las libera ya, no cuando venza su timeout
    await engine.dispose()
    logger.info("database pool closed")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Blog API with JWT authentication, role-based authorization and full CRUD.",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

# Los middleware. El ÚLTIMO que se registra es el de más AFUERA: el primero que ve el
# request y el último que ve la respuesta. Por eso se registran de adentro hacia afuera.
# 1. Rate limiting, el más interno: corta un exceso antes del router y de la base
app.middleware("http")(rate_limit_middleware)
# 2. Errores: atrapa lo que se escape del router (y del rate limiter)
app.middleware("http")(error_handling_middleware)
# 3. Tracing y log: el id se pone antes que nadie; el 429 y el 500 también se loguean
app.middleware("http")(request_logging_middleware)

# 4. CORS, el último registrado: el de más afuera. Toda respuesta lleva sus headers,
# también un 429 o un 500 (sin ellos, el navegador mostraría un error de CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID", "X-Process-Time", "X-RateLimit-Limit",
        "X-RateLimit-Remaining", "Retry-After",
    ],
)


@app.exception_handler(PulseError)
async def pulse_error_handler(request: Request, exc: PulseError) -> JSONResponse:
    content: dict[str, object] = {"detail": exc.detail}
    # Los errores de archivos añaden su código para que el cliente distinga 413 de 415
    if getattr(exc, "error_code", None):
        content["error_code"] = exc.error_code
        content["status_code"] = exc.status_code
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    message = str(exc.orig)
    for fragment, detail in UNIQUE_CONSTRAINTS.items():
        if fragment in message:
            return JSONResponse(status_code=409, content={"detail": detail})
    # Un error de base no previsto: el mismo JSON de 500 que el middleware de errores
    body: dict[str, object] = {
        "detail": "Error interno del servidor",
        "error_code": "INTERNAL_ERROR",
        "status_code": 500,
        "request_id": request_id_var.get(),
    }
    if settings.app_env == "development":
        body["debug"] = {"exception": type(exc).__name__, "message": str(exc)}
    return JSONResponse(status_code=500, content=body)


@app.get("/health", tags=["health"], summary="Health check")
async def health(
    request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    """Responde `healthy` si el servicio está arriba y la base contesta, con el state del pool."""
    # Una consulta mínima: si la base no contesta, falla aquí
    await db.execute(text("SELECT 1"))
    pool = engine.pool
    return {
        "status": "healthy",
        "service": "pulse-api",
        "version": settings.version,
        "database": "ok",
        "uptime_seconds": round(time.monotonic() - request.app.state.started_at, 1),
        "websocket_connections": manager.count(),
        "pool": {
            "size": pool.size(),
            "checked_out": pool.checkedout(),
            "idle": pool.checkedin(),
            "overflow": pool.overflow(),
        },
    }


# Registra todas las rutas de la API: api_router ya trae los routers de cada recurso
app.include_router(api_router)
