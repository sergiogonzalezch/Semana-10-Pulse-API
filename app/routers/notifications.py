"""app/routers/notifications.py
Endpoints HTTP de notificaciones del usuario autenticado.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.dependencies import (
    PaginationParams,
    get_current_user,
    get_notification_service,
)
from app.models import User
from app.schemas.notification import NotificationPage, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(get_current_user)],
    responses={401: {"description": "Falta el token, es inválido o venció"}},
)


@router.get("", response_model=NotificationPage)
async def list_notifications(
    user: User = Depends(get_current_user),
    page: PaginationParams = Depends(),
    unread_only: bool = Query(default=False),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationPage:
    return await service.list_for(user, page, unread_only)


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    return await service.mark_read(notification_id, user)
