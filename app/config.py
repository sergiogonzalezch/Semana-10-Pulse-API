"""app/config.py
Configuración central con pydantic-settings: lee .env y valida los valores.
"""
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores de configuración con defaults seguros para desarrollo."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

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
