# Pulse API — Week 10

Punto de partida: la Week 9 (`pulse-api`) migrada a Alembic y PostgreSQL asíncrono.

## Stack

- Python 3.12+
- FastAPI + Pydantic v2
- SQLAlchemy 2.0 async + `asyncpg`
- Alembic 1.20
- `pwdlib[bcrypt]` + PyJWT
- `httpx` para los scripts de verificación

## Estructura

```text
pulse-api/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── security.py
│   ├── permissions.py
│   ├── exceptions.py
│   ├── dependencies.py
│   ├── middleware/
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   └── routers/
├── migrations/
│   └── versions/
├── scripts/
├── .env.example
├── alembic.ini
├── pyproject.toml
└── README.md
```

## Puesta en marcha

```powershell
cd C:\Users\Sergio\Documents\Cursos\NievaTeam\BackendPython\Semana-10\pulse-api
uv sync
Copy-Item .env.example .env
```

Edita `.env` con tu `DATABASE_URL` y un `JWT_SECRET_KEY` de al menos 32 caracteres. `.env` no se versiona.

## Base de datos

Los tres SQL de la Week 7 están en `..\pulse-blog-db\`:

```powershell
psql -d pulse_blog -f ..\pulse-blog-db\01-schema.sql
psql -d pulse_blog -f ..\pulse-blog-db\02-seed.sql
psql -d pulse_blog -f ..\pulse-blog-db\04-indexes.sql
```

Si la base ya tiene datos, marca la baseline y aplica el resto:

```powershell
uv run alembic stamp 3c8f2a91d0b4
uv run alembic upgrade head
```

Si reconstruiste la base con los SQL anteriores:

```powershell
uv run alembic upgrade head
```

Cadena de revisiones:

```text
3c8f2a91d0b4 (baseline) -> 9e41b7c2a5d6 -> 4b7d9e2f1a63 -> c5e8a1f3b7d2 (head)
```

## Servidor

```powershell
uv run uvicorn app.main:app --reload
```

- Swagger: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## Autenticación y roles

- `POST /auth/register`: registro público, siempre `reader`.
- `POST /auth/login`: formulario OAuth2 (`username` = email, `password`).
- `POST /auth/refresh`: rota el refresh token.
- `POST /auth/logout`: revoca el refresh token.

Roles:

- `reader`: lee contenido publicado y comenta.
- `author`: además crea/edita/borra sus posts.
- `admin`: acceso total.

Contraseña de los usuarios semilla: `pulse-dev-2026`.

Usuarios semilla: `admin@pulse.dev`, `author@pulse.dev`, `reader@pulse.dev`.

## Endpoints

- `/auth`: register, login, refresh, logout.
- `/users`: `me`, listado y alta (admin).
- `/categories`: listado, detalle y alta (admin).
- `/posts`: listado con filtros, detalle por id/slug, alta, patch y borrado.
- `/comments`: listado por `post_id`, alta, patch y borrado.

## Verificación

```powershell
uv run python -m compileall -q app scripts migrations\versions
uv run alembic history
uv run python -m scripts.walkthrough
uv run python -m scripts.access_matrix
```

El recorrido imprime 46 pasos. La matriz imprime los casos de autorización por rol.

## Commits sugeridos

```text
3c8f2a91d0b4_baseline_pulse_blog_schema_from_week_7.py
9e41b7c2a5d6_add_updated_at_to_comments.py
4b7d9e2f1a63_add_hashed_password_to_users.py
c5e8a1f3b7d2_add_refresh_tokens_table.py
```
