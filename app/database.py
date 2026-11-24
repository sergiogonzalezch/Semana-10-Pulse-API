"""app/database.py
Engine asíncrono, fábrica de sesiones y dependencia get_db.
"""
from collections.abc import AsyncGenerator

# text para el SELECT del arranque
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
)
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield una sesión por petición; rollback si hay excepción."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database() -> str:
    """Pide la versión a PostgreSQL. Si no contesta, el arranque falla (fail fast)."""
    try:
        # Una conexión del pool, la consulta más barata que dice algo útil, y se devuelve
        async with engine.connect() as connection:
            version = (await connection.execute(text("SELECT version()"))).scalar_one()
    # Sin servidor, puerto equivocado, contraseña mala: OSError, SQLAlchemyError
    # o el error directo de asyncpg que a veces sube sin envolver
    except Exception as exc:
        # Solo host, puerto y base: la URL completa lleva la contraseña
        where = settings.DATABASE_URL.rsplit("@", 1)[-1]
        raise RuntimeError(f"No hay conexión con PostgreSQL en {where}: {exc}") from exc
    # "PostgreSQL 17.9 ..." -> hasta antes de " on "
    return version.split(" on ")[0]
