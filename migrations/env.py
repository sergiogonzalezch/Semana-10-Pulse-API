import asyncio  # correr las migraciones async
from logging.config import fileConfig  # el logging que configura alembic.ini

from sqlalchemy import pool  # NullPool: una conexión por migración
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config  # el engine async, armado desde alembic.ini

from alembic import context  # el contexto de la migración en curso

from app.config import settings  # la URL sale de los mismos Settings de la app
from app.models import Base  # los modelos: lo que autogenerate compara

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# La URL sale de DATABASE_URL, la misma que usa la app. El .replace escapa los "%"
# (una contraseña con %40, por ejemplo): alembic.ini los leería como interpolación.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# Si alembic.ini tiene configuración de logging, se aplica
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Los modelos de app/models/: autogenerate compara esto contra la base.
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Modo offline (--sql): solo la URL, sin conectarse; imprime el SQL
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_server_default=True,
    )

    # Las migraciones pendientes, dentro de una transacción
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # compare_server_default=True: autogenerate también revisa los DEFAULT de cada columna.
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_server_default=True,
    )

    # Corre las migraciones pendientes en una transacción
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # Un engine async solo para migrar, con la URL que puso set_main_option
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # run_sync corre la función síncrona de Alembic sobre la conexión async
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    # Cierra la conexión al terminar
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    # Arranca el event loop y corre la migración async
    asyncio.run(run_async_migrations())


# --sql es modo offline; lo normal (upgrade, check) es online
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()