"""Recorrido completo de la API: auth, roles, usuarios, categorías, posts, comentarios,
WebSocket, notificaciones, imágenes y export CSV. Crea sus datos y los borra al final.

Manda más requests por minuto que el límite del rate limiter: levanta la API con límites altos.
1. Arranca la API (PowerShell):
   $env:RATE_LIMIT_PER_MINUTE = 1000
   $env:LOGIN_RATE_LIMIT_PER_MINUTE = 1000
   uv run uvicorn app.main:app
2. En otra terminal: uv run python -m scripts.walkthrough
"""
from __future__ import annotations

import base64
import json
import os
import struct
import zlib
from collections.abc import Callable
from typing import Any

import httpx
from websockets.exceptions import InvalidStatus
from websockets.sync.client import connect

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
DEV_PASSWORD = os.getenv("WALKTHROUGH_PASSWORD", "pulse-dev-2026")
ADMIN_EMAIL = os.getenv("WALKTHROUGH_ADMIN_EMAIL", "admin@pulse.dev")
AUTHOR_EMAIL = os.getenv("WALKTHROUGH_AUTHOR_EMAIL", "author@pulse.dev")
READER_EMAIL = os.getenv("WALKTHROUGH_READER_EMAIL", "reader@pulse.dev")

client = httpx.Client(base_url=BASE_URL, timeout=15.0)
tokens: dict[str, str] = {}
ids: dict[str, int] = {}
count = 0


def record(
    description: str, status: object, expected: object, detail: str = ""
) -> None:
    global count
    count += 1
    ok = status == expected
    print(
        f"[{count:02d}] {'OK ' if ok else 'BAD'} {description}: "
        f"{status} (esperado {expected}) {detail}".rstrip()
    )


def step(
    description: str,
    response: httpx.Response,
    expected: int,
    detail: Callable[[httpx.Response], str] | None = None,
) -> httpx.Response:
    extra = detail(response) if detail else ""
    record(description, response.status_code, expected, extra)
    if response.status_code != expected:
        print(response.text[:500])
    assert response.status_code == expected, (
        f"{description}: esperado {expected}, obtenido {response.status_code}"
    )
    return response


def bearer(role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens[role]}"}


def login(email: str) -> dict[str, Any]:
    response = client.post(
        "/auth/login",
        data={"username": email, "password": DEV_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()


def forged(token: str) -> str:
    """El mismo token con un claim cambiado y la firma original: no debe entrar."""
    header, payload, signature = token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    claims["role"] = "admin"
    changed = base64.urlsafe_b64encode(
        json.dumps(claims, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()
    return f"{header}.{changed}.{signature}"


def ws_url(token: str) -> str:
    """http:// se vuelve ws://; el access token va en la query string."""
    return BASE_URL.replace("http", "ws", 1) + f"/api/v1/ws/notifications?token={token}"


def ws_hello(description: str, websocket: Any) -> None:
    hello = json.loads(websocket.recv(timeout=5))
    record(description, hello.get("type"), "connected", f"unread={hello.get('unread')}")


def ws_receive(description: str, websocket: Any) -> None:
    message = json.loads(websocket.recv(timeout=5))
    data = message.get("data", {})
    detail = f"kind={data.get('kind')} de {data.get('actor', {}).get('username')}"
    record(description, message.get("type"), "notification", detail)


def ws_rejected(description: str, token: str) -> None:
    try:
        with connect(ws_url(token)):
            status = "conectado"
    except InvalidStatus as exc:
        status = f"rechazado HTTP {exc.response.status_code}"
    record(description, status, "rechazado HTTP 403")


def tiny_png() -> bytes:
    """Un PNG real de 1x1 píxel: firma, IHDR, IDAT e IEND."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    pixels = zlib.compress(b"\x00\xff\x00\x00")
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", pixels) + chunk(b"IEND", b"")


def main() -> None:
    print(f"Recorrido contra {BASE_URL}\n")

    step("health", client.get("/health"), 200)

    for role, email in (
        ("admin", ADMIN_EMAIL),
        ("author", AUTHOR_EMAIL),
        ("reader", READER_EMAIL),
    ):
        data = login(email)
        tokens[role] = data["access_token"]
        tokens[f"{role}_refresh"] = data["refresh_token"]
        step(f"login {role}", client.get("/users/me", headers=bearer(role)), 200)

    step("users sin token", client.get("/users"), 401)
    users = step("list users admin", client.get("/users", headers=bearer("admin")), 200)
    step("list users reader", client.get("/users", headers=bearer("reader")), 403)
    step("me reader", client.get("/users/me", headers=bearer("reader")), 200)
    step("user ajeno reader", client.get("/users/1", headers=bearer("reader")), 403)

    ids["admin"] = int(users.json()[0]["id"])
    new_user = {
        "username": "walkthrough_user",
        "email": "walkthrough@pulse.dev",
        "password": "walkthrough-pass-2026",
        "role": "reader",
    }
    created = step(
        "create user admin",
        client.post("/users", json=new_user, headers=bearer("admin")),
        201,
    )
    step(
        "create user duplicado",
        client.post("/users", json=new_user, headers=bearer("admin")),
        409,
    )
    step(
        "register público",
        client.post(
            "/auth/register",
            json={
                "username": "walkthrough_public",
                "email": "walkthrough-public@pulse.dev",
                "password": "walkthrough-pass-2026",
            },
        ),
        201,
    )
    step(
        "register duplicado",
        client.post(
            "/auth/register",
            json={
                "username": "walkthrough_public",
                "email": "walkthrough-public@pulse.dev",
                "password": "walkthrough-pass-2026",
            },
        ),
        409,
    )
    public_token = login("walkthrough-public@pulse.dev")["access_token"]
    step(
        "login usuario registrado",
        client.get(
            "/users/me", headers={"Authorization": f"Bearer {public_token}"}
        ),
        200,
    )
    step(
        "me usuario registrado",
        client.get(
            "/users/me", headers={"Authorization": f"Bearer {public_token}"}
        ),
        200,
    )

    categories = step("list categories", client.get("/categories"), 200)
    step("list categories paginado", client.get("/categories?limit=2&offset=1"), 200)
    ids["category"] = int(categories.json()[0]["id"])
    new_category = {
        "name": "Walkthrough Category",
        "slug": "walkthrough-category",
        "description": "Creada por el recorrido",
    }
    step(
        "create category reader",
        client.post("/categories", json=new_category, headers=bearer("reader")),
        403,
    )
    cat = step(
        "create category admin",
        client.post("/categories", json=new_category, headers=bearer("admin")),
        201,
    )
    ids["new_category"] = int(cat.json()["id"])
    step(
        "create category duplicada",
        client.post("/categories", json=new_category, headers=bearer("admin")),
        409,
    )
    step(
        "get category",
        client.get(f"/categories/{ids['new_category']}"),
        200,
    )
    step("get category inexistente", client.get("/categories/999999"), 404)
    step("list categories paginación inválida", client.get("/categories?limit=0"), 422)
    step(
        "get category con token",
        client.get(f"/categories/{ids['new_category']}", headers=bearer("reader")),
        200,
    )

    public_posts = step("list posts público", client.get("/posts"), 200)
    step("list posts reader", client.get("/posts", headers=bearer("reader")), 200)
    step("list posts limitado", client.get("/posts?limit=5&offset=1"), 200)
    step(
        "list posts por categoria",
        client.get(f"/posts?category_id={ids['category']}"),
        200,
    )
    step(
        "list drafts reader",
        client.get("/posts?status=draft", headers=bearer("reader")),
        403,
    )
    step("list posts paginación inválida", client.get("/posts?limit=0"), 422)
    step("list drafts sin token", client.get("/posts?status=draft"), 403)
    drafts = step(
        "list drafts author",
        client.get("/posts?status=draft", headers=bearer("author")),
        200,
    )
    published = next(p for p in public_posts.json()["items"] if p["status"] == "published")
    draft = drafts.json()["items"][0]
    ids["published"] = int(published["id"])
    ids["draft"] = int(draft["id"])

    step("get post publicado", client.get(f"/posts/{ids['published']}"), 200)
    step("get post por slug", client.get(f"/posts/slug/{published['slug']}"), 200)
    step("get post inexistente", client.get("/posts/999999"), 404)
    step("get draft sin token", client.get(f"/posts/{ids['draft']}"), 404)
    step("get draft admin", client.get(f"/posts/{ids['draft']}", headers=bearer("admin")), 200)

    new_post = {
        "title": "Walkthrough Post",
        "slug": "walkthrough-post",
        "body": "Contenido del post creado por el recorrido automatizado.",
        "excerpt": "Resumen del recorrido",
        "status": "draft",
        "category_id": ids["category"],
        "tag_ids": [],
    }
    step(
        "create post reader",
        client.post("/posts", json=new_post, headers=bearer("reader")),
        403,
    )
    post = step(
        "create post author",
        client.post("/posts", json=new_post, headers=bearer("author")),
        201,
    )
    ids["new_post"] = int(post.json()["id"])
    step(
        "create post slug duplicado",
        client.post("/posts", json=new_post, headers=bearer("author")),
        409,
    )
    step(
        "patch post propio",
        client.patch(
            f"/posts/{ids['new_post']}",
            json={"title": "Walkthrough Post Actualizado"},
            headers=bearer("author"),
        ),
        200,
    )

    # Tiempo real: el author escucha, el reader comenta y el aviso llega por WebSocket.
    step(
        "publicar post creado",
        client.patch(
            f"/posts/{ids['new_post']}",
            json={"status": "published"},
            headers=bearer("author"),
        ),
        200,
    )
    png = tiny_png()
    with connect(ws_url(tokens["author"])) as author_ws:
        ws_hello("WS saludo author", author_ws)
        step(
            "reader comenta el post del author",
            client.post(
                f"/posts/{ids['new_post']}/comments",
                json={"body": "Comentario con notificación en vivo."},
                headers=bearer("reader"),
            ),
            201,
        )
        ws_receive("WS notificación", author_ws)

    notifications = step(
        "notificaciones del author",
        client.get("/notifications", headers=bearer("author")),
        200,
    )
    notification = next(
        (
            item
            for item in notifications.json()["items"]
            if item["post_id"] == ids["new_post"]
        ),
        None,
    )
    assert notification is not None, "el comentario no creó la notificación"
    ids["notification"] = notification["id"]
    step(
        "marcar notificación ajena",
        client.put(
            f"/notifications/{ids['notification']}/read", headers=bearer("reader")
        ),
        404,
    )
    step(
        "marcar notificación leída",
        client.put(
            f"/notifications/{ids['notification']}/read", headers=bearer("author")
        ),
        200,
    )
    ws_rejected("WS con token adulterado", forged(tokens["reader"]))

    # Imágenes: solo el dueño, JPEG/PNG de verdad, y descarga pública del post publicado.
    step(
        "subir imagen sin ser dueño",
        client.post(
            f"/posts/{ids['new_post']}/image",
            files={"file": ("cover.png", png, "image/png")},
            headers=bearer("reader"),
        ),
        403,
    )
    step(
        "subir imagen falsa",
        client.post(
            f"/posts/{ids['new_post']}/image",
            files={"file": ("fake.png", b"not an image", "image/png")},
            headers=bearer("author"),
        ),
        415,
    )
    step(
        "subir imagen PNG",
        client.post(
            f"/posts/{ids['new_post']}/image",
            files={"file": ("cover.png", png, "image/png")},
            headers=bearer("author"),
        ),
        200,
        detail=lambda r: f"image_url={r.json().get('image_url')}",
    )
    step(
        "descargar imagen",
        client.get(f"/posts/{ids['new_post']}/image"),
        200,
        detail=lambda r: f"{r.headers.get('content-type')} {len(r.content)} bytes",
    )
    step(
        "exportar CSV",
        client.get("/posts/export"),
        200,
        detail=lambda r: f"{len(r.text.splitlines())} líneas",
    )

    admin_posts = step(
        "list posts admin",
        client.get(f"/posts?author_id={ids['admin']}", headers=bearer("admin")),
        200,
    )
    ids["admin_post"] = int(admin_posts.json()["items"][0]["id"])
    step(
        "patch post ajeno",
        client.patch(
            f"/posts/{ids['admin_post']}",
            json={"title": "Intento de modificación"},
            headers=bearer("author"),
        ),
        403,
    )

    step(
        "list comments",
        client.get(f"/comments?post_id={ids['published']}"),
        200,
    )
    step("comments post inexistente", client.get("/comments?post_id=999999"), 404)
    comment = step(
        "create comment reader",
        client.post(
            f"/posts/{ids['published']}/comments",
            json={"body": "Comentario del recorrido"},
            headers=bearer("reader"),
        ),
        201,
    )
    ids["comment"] = int(comment.json()["id"])
    step(
        "create comment sin token",
        client.post(
            f"/posts/{ids['draft']}/comments",
            json={"body": "Comentario anónimo"},
        ),
        401,
    )
    step(
        "patch comment inexistente",
        client.patch(
            "/comments/999999",
            json={"body": "Comentario inexistente"},
            headers=bearer("reader"),
        ),
        404,
    )
    step(
        "patch comment ajeno",
        client.patch(
            f"/comments/{ids['comment']}",
            json={"body": "Modificación ajena"},
            headers=bearer("author"),
        ),
        403,
    )
    step(
        "patch comment propio",
        client.patch(
            f"/comments/{ids['comment']}",
            json={"body": "Comentario editado"},
            headers=bearer("reader"),
        ),
        200,
    )
    step(
        "delete comment admin",
        client.delete(f"/comments/{ids['comment']}", headers=bearer("admin")),
        204,
    )

    old_refresh = tokens["admin_refresh"]
    refreshed = step(
        "refresh token",
        client.post("/auth/refresh", json={"refresh_token": old_refresh}),
        200,
    )
    tokens["admin_refresh"] = refreshed.json()["refresh_token"]
    step(
        "refresh reutilizado",
        client.post("/auth/refresh", json={"refresh_token": old_refresh}),
        401,
    )
    step(
        "logout",
        client.post(
            "/auth/logout", json={"refresh_token": tokens["admin_refresh"]}
        ),
        204,
    )
    step(
        "token inválido",
        client.get("/users/me", headers={"Authorization": "Bearer not-a-jwt"}),
        401,
    )
    traced = step(
        "health con request id",
        client.get("/health", headers={"X-Request-ID": "walkthrough-70"}),
        200,
    )
    assert traced.headers.get("X-Request-ID") == "walkthrough-70"
    step(
        "delete post author",
        client.delete(f"/posts/{ids['new_post']}", headers=bearer("author")),
        204,
    )

    assert count == 70, f"El recorrido tiene {count} pasos, no 70"
    print(f"\nRecorrido completado: {count}/70 pasos correctos.")


if __name__ == "__main__":
    main()
