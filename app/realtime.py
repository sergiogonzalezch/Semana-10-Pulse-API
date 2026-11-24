"""app/realtime.py
Conexiones WebSocket activas por usuario, en memoria del proceso.
"""
from __future__ import annotations

from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active[user_id].add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        connections = self.active.get(user_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self.active.pop(user_id, None)

    def count(self, user_id: int | None = None) -> int:
        if user_id is None:
            return sum(len(connections) for connections in self.active.values())
        return len(self.active.get(user_id, ()))

    async def send_to_user(self, user_id: int, message: dict[str, object]) -> int:
        dead: list[WebSocket] = []
        connections = list(self.active.get(user_id, ()))
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(user_id, websocket)
        return len(connections) - len(dead)


manager = ConnectionManager()
