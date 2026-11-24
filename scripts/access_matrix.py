"""scripts/access_matrix.py
Matriz rápida de accesos por rol para comprobar la autorización.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
DEV_PASSWORD = os.getenv("WALKTHROUGH_PASSWORD", "pulse-dev-2026")


@dataclass(frozen=True)
class Case:
    name: str
    role: str | None
    method: str
    path: str
    expected: int
    json: dict[str, object] | None = None


CASES: list[Case] = [
    Case("health público", None, "GET", "/health", 200),
    Case("users anónimo", None, "GET", "/users", 401),
    Case("users reader", "reader", "GET", "/users", 403),
    Case("users admin", "admin", "GET", "/users", 200),
    Case("me reader", "reader", "GET", "/users/me", 200),
    Case("posts público", None, "GET", "/posts", 200),
    Case("drafts anónimo", None, "GET", "/posts?status=draft", 403),
    Case("drafts author", "author", "GET", "/posts?status=draft", 200),
    Case("categorías público", None, "GET", "/categories", 200),
    Case(
        "crear categoría reader",
        "reader",
        "POST",
        "/categories",
        403,
        {"name": "Matrix", "slug": "matrix", "description": None},
    ),
    Case(
        "crear post reader",
        "reader",
        "POST",
        "/posts",
        403,
        {
            "title": "Matrix Post",
            "slug": "matrix-post",
            "body": "Cuerpo del post de la matriz",
            "status": "draft",
        },
    ),
    Case(
        "crear post author",
        "author",
        "POST",
        "/posts",
        201,
        {
            "title": "Matrix Post Author",
            "slug": "matrix-post-author",
            "body": "Cuerpo del post de la matriz",
            "status": "draft",
        },
    ),
    Case("post inexistente", None, "GET", "/posts/999999", 404),
    Case("comentarios anónimos", None, "GET", "/comments?post_id=1", 200),
]


def login(email: str, client: httpx.Client) -> str:
    response = client.post(
        "/auth/login",
        data={"username": email, "password": DEV_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
        tokens = {
            role: login(f"{role}@pulse.dev", client)
            for role in ("admin", "author", "reader")
        }
        failures = 0
        for case in CASES:
            headers = (
                {"Authorization": f"Bearer {tokens[case.role]}"}
                if case.role
                else {}
            )
            response = client.request(
                case.method,
                case.path,
                headers=headers,
                json=case.json,
            )
            ok = response.status_code == case.expected
            print(
                f"{'OK ' if ok else 'BAD'} {case.name}: "
                f"{response.status_code} (esperado {case.expected})"
            )
            failures += 0 if ok else 1
        print(f"\nMatriz: {len(CASES) - failures}/{len(CASES)} casos correctos.")
        assert failures == 0


if __name__ == "__main__":
    main()
