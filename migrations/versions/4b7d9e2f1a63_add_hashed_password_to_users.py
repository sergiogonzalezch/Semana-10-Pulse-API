"""add hashed_password to users

Tres pasos en una migración (una sola transacción): la columna nace nullable, se llena
para los usuarios que ya existen y recién entonces pasa a NOT NULL. Con el NOT NULL
directo, como la generó autogenerate, falla: los 12 usuarios del seed quedarían en NULL.

Revision ID: 4b7d9e2f1a63
Revises: 9e41b7c2a5d6
Create Date: 2026-09-23 20:27:43.704395

"""
# Tipos para las anotaciones de los ids de revisión
from typing import Sequence, Union

# op ejecuta los cambios de schema; sa describe columnas y tablas
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
# Esta revisión y la anterior: así Alembic encadena la historia
revision: str = '4b7d9e2f1a63'
down_revision: Union[str, Sequence[str], None] = '9e41b7c2a5d6'
# Sin ramas ni dependencias extra
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# El hash bcrypt de la contraseña de desarrollo del seed (la dice el README). Se calculó una
# vez con app.security; aquí solo está el hash. Solo para desarrollo: en producción no se
# inventa una contraseña, se obliga a cada usuario a crear la suya.
DEV_PASSWORD_HASH = "$2b$12$yu99JN2iALllVNB6dqF2ludd3ePOJQ/yQSych/H2AN9UMsxN5YBVi"


def upgrade() -> None:
    """Upgrade schema."""
    # 1. La columna, todavía nullable: las filas que ya existen quedan en NULL.
    op.add_column('users', sa.Column('hashed_password', sa.String(length=255), nullable=True))

    # 2. El backfill. Una tabla "liviana" (sa.table) y no el modelo User: el modelo va a
    # cambiar en migraciones futuras, y esta migración tiene que seguir corriendo igual.
    users = sa.table("users", sa.column("hashed_password", sa.String))
    # UPDATE users SET hashed_password = ... WHERE hashed_password IS NULL
    op.execute(
        users.update()
        .where(users.c.hashed_password.is_(None))
        .values(hashed_password=DEV_PASSWORD_HASH)
    )

    # 3. Ahora sí, NOT NULL: ninguna fila quedó sin hash.
    op.alter_column('users', 'hashed_password', existing_type=sa.String(length=255), nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Borra los hashes. Volver a subir le pone a todos la contraseña de desarrollo.
    op.drop_column('users', 'hashed_password')
