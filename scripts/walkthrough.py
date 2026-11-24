"""scripts/walkthrough.py
Recorrido de 46 pasos: auth, roles, usuarios, categorías, posts y comentarios.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
DEV_PASSWORD = os.getenv("WALKTHROUGH_PASSWORD", "pulse-dev-2026")
ADMIN_EMAIL = os.getenv("WALKTHROUGH_ADMIN_EMAIL", "admin@pulse.dev")
AUTHOR_EMAIL = os.getenv("WALKTHROUGH_AUTHOR_EMAIL", "author@pulse.dev")
READER_EMAIL = os.getenv("WALKTHROUGH_READER_EMAIL", "reader@pulse.dev")

client = httpx.Client(base_url=BASE_URL, timeout=15.0)
tokens: dict[str, str] = {}
ids: dict[str, int] = {}
count = 0


def step(description: str, response: httpx.Response, expected: int) -> httpx.Response:
    global count
    count += 1
    ok = response.status_code == expected
    print(
        f"[{count:02d}/46] {'OK ' if ok else 'BAD'} {description}: "
        f"{response.status_code} (esperado {expected})"
    )
    if not ok:
        print(response.text[:500])
    assert ok, f"{description}: esperado {expected}, obtenido {response.status_code}"
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
        client.get("/health", headers={"X-Request-ID": "walkthrough-46"}),
        200,
    )
    assert traced.headers.get("X-Request-ID") == "walkthrough-46"
    step(
        "delete post author",
        client.delete(f"/posts/{ids['new_post']}", headers=bearer("author")),
        204,
    )

    assert count == 46, f"El recorrido tiene {count} pasos, no 46"
    print(f"\nRecorrido completado: {count}/46 pasos correctos.")


if __name__ == "__main__":
    main()
