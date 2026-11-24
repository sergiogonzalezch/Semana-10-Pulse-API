"""app/routers/ws.py
Canal WebSocket de notificaciones y cliente HTML de prueba.
"""
from __future__ import annotations

from pathlib import Path

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse

from app.database import async_session_factory
from app.models import User
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repo import UserRepository
from app.realtime import manager
from app.schemas.user import UserResponse
from app.security import ACCESS, decode_token

router = APIRouter(prefix="/ws", tags=["realtime"])
STATIC_CLIENT = Path(__file__).resolve().parent.parent / "static" / "ws_client.html"


async def authenticate(token: str | None) -> tuple[User, int] | None:
    if not token:
        return None
    try:
        payload = decode_token(token, ACCESS)
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        return None
    async with async_session_factory() as db:
        user = await UserRepository(db).get(user_id)
        if user is None or not user.is_active:
            return None
        unread = await NotificationRepository(db).count_unread(user.id)
    return user, unread


@router.websocket("/notifications")
async def ws_notifications(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    authenticated = await authenticate(token)
    if authenticated is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    user, unread = authenticated
    await manager.connect(user.id, websocket)
    await websocket.send_json(
        {
            "type": "connected",
            "user": UserResponse.model_validate(user).model_dump(mode="json"),
            "unread": unread,
        }
    )
    try:
        while True:
            text = await websocket.receive_text()
            if text == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(user.id, websocket)


@router.get("/client", response_class=FileResponse)
async def ws_client() -> FileResponse:
    return FileResponse(STATIC_CLIENT)
