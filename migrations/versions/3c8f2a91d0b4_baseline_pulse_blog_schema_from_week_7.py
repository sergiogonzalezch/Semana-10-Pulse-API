"""baseline: pulse_blog schema from week 7

Vacía a propósito: las seis tablas ya existen, las crearon 01-schema.sql y
04-indexes.sql de la Week 7. Una pulse_blog que ya tiene datos se marca con
`alembic stamp head`; una reconstruida con los archivos de la Week 7 también
acepta `alembic upgrade head` (esta revisión no ejecuta nada).

Revision ID: 3c8f2a91d0b4
Revises:
Create Date: 2026-09-23 18:00:00.123456

"""
# Tipos para las anotaciones de los ids de revisión
from typing import Sequence, Union

# op ejecuta los cambios de schema; sa describe columnas y tablas
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
# El id de esta revisión
revision: str = '3c8f2a91d0b4'
# None: es la primera de la cadena
down_revision: Union[str, Sequence[str], None] = None
# Sin ramas ni dependencias extra
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# upgrade no hace nada: las tablas ya las creó el SQL de la Week 7
def upgrade() -> None:
    """Upgrade schema."""
    pass  # nada que crear


# downgrade tampoco: bajar de la baseline no borra tablas
def downgrade() -> None:
    """Downgrade schema."""
    pass  # nada que deshacer
