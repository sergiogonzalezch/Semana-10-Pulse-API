"""scripts/ws_listen.py
Cliente WebSocket de terminal: hace login y escucha notificaciones.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from urllib.parse import quote, urlsplit

import httpx
from websockets.asyncio.client import connect


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Escucha notificaciones de Pulse")
    parser.add_argument("--username", default="admin", help="usuario o email de login")
    parser.add_argument("--password", default="pulse-dev-2026")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", help="access token ya obtenido")
    parser.add_argument("--count", type=int, default=5, help="mensajes a imprimir")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    token = args.token
    if token is None:
        with httpx.Client(base_url=args.base_url, timeout=10.0) as client:
            response = client.post(
                "/api/v1/auth/login",
                data={"username": args.username, "password": args.password},
            )
            response.raise_for_status()
            token = response.json()["access_token"]

    url = urlsplit(args.base_url)
    scheme = "wss" if url.scheme == "https" else "ws"
    host = url.netloc or "127.0.0.1:8000"
    websocket_url = f"{scheme}://{host}/api/v1/ws/notifications?token={quote(token)}"

    async with connect(websocket_url) as websocket:
        print(await websocket.recv())
        for _ in range(args.count):
            message = json.loads(await websocket.recv())
            print(json.dumps(message, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
