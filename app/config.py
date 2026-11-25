"""app/config.py
Configuración central con pydantic-settings: lee .env y valida los valores.
"""
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores de configuración con defaults seguros para desarrollo."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Nombre y versión que muestran /docs y el health check
    app_name: str = "Pulse API"
    version: str = "0.3.0"

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://pulse:pulse@localhost:5432/pulse_blog"
    )
    JWT_SECRET_KEY: str = Field(
        default="dev-only-secret-change-me-in-real-environments"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Las background tasks (Week 10). Los archivos van en var/, que git ignora.
    # El "email" es simulado: tarda EMAIL_DELAY_SECONDS y se escribe en outbox.log
    email_delay_seconds: float = 2.0
    outbox_path: Path = Path("var/outbox.log")
    # Los eventos de analytics, una línea JSON por evento
    analytics_path: Path = Path("var/analytics.log")

    # Las imágenes de los posts (Week 10): la carpeta y el tamaño máximo (5 MB)
    upload_dir: Path = Path("var/uploads")
    max_image_bytes: int = 5 * 1024 * 1024

    # Middleware (Week 10). En producción, APP_ENV=production: los 500 no dan detalles.
    app_env: Literal["development", "production"] = "development"
    # Requests por minuto por IP: el general y el del login (fuerza bruta)
    rate_limit_per_minute: int = 30
    login_rate_limit_per_minute: int = 5

    @field_validator("DATABASE_URL")
    @classmethod
    def require_asyncpg(cls, v: str) -> str:
        """Exige el driver asyncpg para SQLAlchemy AsyncSession."""
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must start with postgresql+asyncpg://")
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def require_strong_secret(cls, v: str) -> str:
        """Evita secretos demasiado cortos en desarrollo."""
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v


settings = Settings()
