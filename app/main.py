"""app/main.py
Punto de entrada: app FastAPI, CORS, handlers de error, health check y routers.
"""
from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app import __version__
from app.config import settings
from app.database import check_db, engine
from app.exceptions import PulseError, UNIQUE_CONSTRAINTS
from app.middleware.request_logging import RequestLoggingMiddleware
# El router de la versión 1, con todos los routers adentro
from app.api import api_router


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
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Arranque y apagado: solo disposición del engine al cerrar."""
    yield
    await engine.dispose()


app = FastAPI(
    title="Pulse API",
    version=__version__,
    description="Blog API with JWT authentication, role-based authorization and full CRUD.",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)


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
    return JSONResponse(status_code=500, content={"detail": "Database integrity error"})


@app.get("/health", tags=["health"])
async def health() -> dict[str, object]:
    database_ok = await check_db()
    return {
        "status": "ok" if database_ok else "degraded",
        "version": __version__,
        "database": "connected" if database_ok else "unavailable",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# Registra todas las rutas de la API: api_router ya trae los routers de cada recurso
app.include_router(api_router)
