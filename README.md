# pulse-api

The REST API of **Pulse**, a blogging platform, on top of the `pulse_blog`
PostgreSQL database from Week 7. Built with FastAPI, SQLAlchemy 2.0 (async, with
asyncpg), Alembic and pydantic-settings. It has JWT authentication with bcrypt,
roles and ownership, a versioned router, WebSocket notifications, background
tasks, post images, a streaming CSV export, startup checks, and middleware for
rate limiting, request tracing and unhandled errors. Version **0.3.0**.

## Stack

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- FastAPI and Pydantic v2
- SQLAlchemy 2.0 with `AsyncSession` and the `asyncpg` driver
- Alembic for migrations
- pydantic-settings (configuration from `.env`)
- pwdlib with bcrypt (password hashing) and PyJWT (HS256 tokens)
- WebSockets and `BackgroundTasks`
- aiofiles and python-multipart (async file writes and uploads)
- PostgreSQL 16+ (17 recommended)

## Setup

1. Have the Week 7 database ready. The three SQL files live in `../pulse-blog-db/`:

   ```powershell
   psql -d pulse_blog -f ..\pulse-blog-db\01-schema.sql
   psql -d pulse_blog -f ..\pulse-blog-db\02-seed.sql
   psql -d pulse_blog -f ..\pulse-blog-db\04-indexes.sql
   ```

   If the database already has data, stamp the baseline and migrate instead:

   ```powershell
   uv run alembic stamp 3c8f2a91d0b4
   uv run alembic upgrade head
   ```

2. Install dependencies and create your `.env` (from this folder):

   ```powershell
   uv sync
   Copy-Item .env.example .env
   uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   Put that value in `JWT_SECRET_KEY` (at least 32 characters). `.env` holds
   secrets and is git-ignored; `.env.example` is committed. Run every command
   from this folder: settings are read from `.env` in the current directory.
   Exported environment variables win over `.env`.

3. Bring the schema to the latest migration:

   ```powershell
   uv run alembic upgrade head
   ```

## Development users

The seed users share the **development-only** password `pulse-dev-2026`.

| Email | Username | Role | Notes |
|---|---|---|---|
| `admin@pulse.dev` | `admin` | admin | full access |
| `author@pulse.dev` | `author` | author | can write posts |
| `reader@pulse.dev` | `reader` | reader | can comment |
| `heidi@pulse.dev` | `heidi` | reader | inactive: login fails |

## Run

```powershell
uv run uvicorn app.main:app
```

At startup the app runs `SELECT version()` and creates `var/`, `var/uploads`,
`var/outbox.log` and `var/analytics.log`. If PostgreSQL is not reachable the
app does not start (fail fast).

- API docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health (database, pool, uptime, open WebSockets)
- WebSocket test page: http://127.0.0.1:8000/api/v1/ws/client

```powershell
# form data, not JSON; the username is the email
curl -X POST http://127.0.0.1:8000/api/v1/auth/login `
  -d 'username=author@pulse.dev&password=pulse-dev-2026'
```

The walkthrough and the access matrix send dozens of requests in a few seconds,
more than the default rate limit of 30 per minute. Do **not** disable the rate
limiter for them: start the API with higher limits through environment
variables (they win over the defaults in `app/config.py`):

```powershell
$env:RATE_LIMIT_PER_MINUTE = 1000
$env:LOGIN_RATE_LIMIT_PER_MINUTE = 1000
uv run uvicorn app.main:app
```

In another terminal, with those variables in the server process:

```powershell
uv run python -m scripts.walkthrough
uv run python -m scripts.access_matrix
uv run python -m scripts.list_routes
uv run python -m scripts.ws_listen author
```

The walkthrough creates its own data, deletes what it can at the end, and now
also opens a WebSocket, uploads an image and downloads the CSV. `ws_listen`
waits for notifications; stop it with Ctrl+C. `list_routes` prints one HTTP
route per line (the WebSocket is not in OpenAPI).

## Configuration

`DATABASE_URL` and `JWT_SECRET_KEY` have safe development defaults in this
checkout; set real values in `.env` before using the app outside your machine.
Every other setting has a default and can be overridden in `.env` or the
environment.

| Variable | Default | What it does |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://pulse:pulse@localhost:5432/pulse_blog` | Async PostgreSQL URL (must use `+asyncpg`) |
| `JWT_SECRET_KEY` | development value | HS256 signing key, at least 32 characters |
| `APP_ENV` | `development` | `production` hides the exception type and message in 500 responses |
| `RATE_LIMIT_PER_MINUTE` | `30` | Requests per minute per IP, all routes |
| `LOGIN_RATE_LIMIT_PER_MINUTE` | `5` | Requests per minute per IP to `POST /api/v1/auth/login` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `EMAIL_DELAY_SECONDS` | `2.0` | Simulated email delay |
| `OUTBOX_PATH` | `var/outbox.log` | Where simulated emails are written |
| `ANALYTICS_PATH` | `var/analytics.log` | One JSON line per analytics event |
| `UPLOAD_DIR` | `var/uploads` | Post images |
| `MAX_IMAGE_BYTES` | `5242880` | 5 MB |

## Authentication

- `POST /api/v1/auth/login` uses the OAuth2 password flow (form data,
  `username` = email) and returns an access token (15 minutes) and a refresh
  token (7 days).
- Send `Authorization: Bearer <access_token>` on protected routes.
- `POST /api/v1/auth/refresh` rotates the refresh token: each one works once;
  reusing a spent one revokes the session.
- `POST /api/v1/auth/logout` revokes a refresh token. The access token keeps
  working until it expires.

Access token claims: `sub` (user id as a string), `type`, `iat`, `exp`, `jti`.
The user and role are loaded from the database on every request, so a role
change or a deactivated account applies immediately.

Rate limiting is per IP and per process: the sliding-window limiter lives in
memory, like the WebSocket manager. Restarting the server clears it, and with
several workers each one counts independently.

## Endpoints

Auth column: **public**, **optional** (more data with a token), **user** (any
active user), **author+**, **admin**, **owner** (the post/comment author or an
admin).

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | public | Health check, pool and WebSocket count |
| POST | `/api/v1/auth/register` | public | Register a reader account |
| POST | `/api/v1/auth/login` | public | Login with form data |
| POST | `/api/v1/auth/refresh` | public | Rotate the refresh token |
| POST | `/api/v1/auth/logout` | public | Revoke the refresh token |
| GET | `/api/v1/users/me` | user | The user of the token |
| GET | `/api/v1/users` | admin | List users (`skip`, `limit`) |
| POST | `/api/v1/users` | admin | Create a user with a chosen role |
| GET | `/api/v1/users/{user_id}` | admin | Get a user |
| GET | `/api/v1/categories` | public | List categories |
| POST | `/api/v1/categories` | admin | Create a category |
| GET | `/api/v1/categories/{category_id}` | public | Get a category |
| GET | `/api/v1/posts` | optional | Page of visible posts (`status`, `author_id`, `category_id`, `tag_id`) |
| POST | `/api/v1/posts` | author+ | Create a post |
| GET | `/api/v1/posts/export` | optional | Streamed CSV of visible posts |
| GET | `/api/v1/posts/slug/{slug}` | optional | Get a post by slug |
| GET | `/api/v1/posts/{post_id}` | optional | Get a post by id |
| PATCH | `/api/v1/posts/{post_id}` | owner | Partial update |
| DELETE | `/api/v1/posts/{post_id}` | owner | Delete the post, comments, tags and image |
| POST | `/api/v1/posts/{post_id}/image` | owner | Upload a JPEG or PNG (multipart field `file`, 5 MB) |
| GET | `/api/v1/posts/{post_id}/image` | optional | Download the image |
| GET | `/api/v1/comments` | optional | Comments of a post (`post_id`) |
| POST | `/api/v1/posts/{post_id}/comments` | user | Comment; notifies the post author |
| PATCH | `/api/v1/comments/{comment_id}` | owner | Edit a comment |
| DELETE | `/api/v1/comments/{comment_id}` | owner | Delete a comment |
| GET | `/api/v1/notifications` | user | Your notifications, newest first |
| PUT | `/api/v1/notifications/{id}/read` | user | Mark one of yours as read |
| WS | `/api/v1/ws/notifications?token=<access>` | user | Real-time notifications |
| GET | `/api/v1/ws/client` | public | Browser test page for the WebSocket |

## Middleware and errors

Middleware is registered from the inside out, because in Starlette the **last
one registered is the outermost**: rate limiting, errors, tracing, then CORS.
A 429 or a 500 therefore still carries CORS headers and `X-Request-ID`.

Every response carries `X-Request-ID` (send your own header to choose it) and
`X-Process-Time`. Responses that passed the rate limiter also carry
`X-RateLimit-Limit` and `X-RateLimit-Remaining`. A 429 adds `Retry-After`.
Every log line of the app, including background tasks, includes the request id
in brackets; startup and shutdown lines show `-`.

Business errors share one format:

```json
{"detail": "Post not found", "error_code": "NOT_FOUND", "status_code": 404}
```

| Status | Meaning |
|---|---|
| 401 / 403 | Authentication failed / not allowed |
| 404 / 409 | Missing resource / duplicate value |
| 413 / 415 | Image too large / not a real JPEG or PNG |
| 429 | Rate limit exceeded (`RATE_LIMITED`, `Retry-After`) |
| 500 | Unhandled error (`INTERNAL_ERROR`, `request_id`, plus `debug` only in development) |

A 500 includes the id needed to find the full traceback in the server log.
In production (`APP_ENV=production`) no exception type or message is sent.

## Background tasks

They run after the response is sent, in the same process:

| When | Task | Where to see it |
|---|---|---|
| Someone comments on your post | WebSocket push of the stored notification | `scripts.ws_listen`, the test page |
| Someone comments on your post | Simulated email (waits `EMAIL_DELAY_SECONDS`) | `var/outbox.log` |
| Someone registers | Analytics event | `var/analytics.log` |

Each task opens its own database session and catches its own errors; they are
not persistent (a restart loses pending tasks).

## Project structure

```text
pulse-api/
├── app/
│   ├── main.py                 app, lifespan, middleware, error handlers, health
│   ├── api.py                  api_router under /api/v1
│   ├── config.py               pydantic-settings (environment and .env)
│   ├── database.py             async engine, session factory, startup check
│   ├── security.py             bcrypt and JWT
│   ├── permissions.py          visibility and owner-or-admin rules
│   ├── exceptions.py           PulseError and unique-violation mapping
│   ├── realtime.py             WebSocket connection manager
│   ├── tasks.py                background tasks
│   ├── storage.py              image validation and disk storage
│   ├── dependencies.py         services, current user, roles, pagination
│   ├── middleware/             request_logging.py, errors.py, rate_limit.py
│   ├── models/ schemas/ repositories/ services/ routers/
│   └── static/ws_client.html   WebSocket test page
├── migrations/versions/        six Alembic revisions
├── scripts/                    walkthrough, access_matrix, list_routes, ws_listen
├── .env.example
├── pyproject.toml
└── var/                        git-ignored runtime files
```

## Migrations

| Revision | What it does |
|---|---|
| `3c8f2a91d0b4` | Baseline: Week 7 schema (no-op) |
| `9e41b7c2a5d6` | Add `comments.updated_at` |
| `4b7d9e2f1a63` | Add `users.hashed_password` |
| `c5e8a1f3b7d2` | Add `refresh_tokens` |
| `d4a7e1c9b2f5` | Add `notifications` |
| `e8b3f6a2c9d1` | Add `posts.image_filename` |

```powershell
uv run alembic current
uv run alembic history
uv run alembic check
uv run alembic downgrade -1
```

## Design decisions

- **Layers:** routers do HTTP, services own business rules and commits,
  repositories only do SQL, and schemas define what comes in and goes out.
- **One versioned router:** `/api/v1` is set once in `app/api.py`.
- **Fail fast at startup:** no database, no app.
- **Notifications are stored, then pushed:** the comment and its notification
  are committed together; the WebSocket push is best effort.
- **The WebSocket authenticates before `accept()`**, with a short-lived access
  token in the query string (browsers cannot set headers on a WebSocket).
- **Slow work runs in background tasks**, which only receive ids and log their
  own errors.
- **Images are validated by their bytes**, saved under a random name and
  deleted with their post.
- **The CSV export is streamed**, so memory stays flat.
- **Middleware order matters:** CORS is outermost so that even a 429 or 500
  carries CORS headers; tracing is outside errors and rate limiting so every
  response is traced and logged.

## Not implemented yet

Shared rate limiting and WebSocket fan-out across processes (Redis), a
persistent task queue, a real email provider, image resizing, cleanup of
expired refresh tokens, and revoking an access token before it expires.
