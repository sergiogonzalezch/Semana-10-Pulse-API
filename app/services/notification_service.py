"""app/services/notification_service.py
Listado y lectura de notificaciones de un usuario.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func

from app.exceptions import NotFoundError
from app.models import User
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationPage, NotificationResponse

if TYPE_CHECKING:
    from app.dependencies import PaginationParams


class NotificationService:
    def __init__(self, notifications: NotificationRepository) -> None:
        self.notifications = notifications

    async def list_for(
        self,
        user: User,
        page: PaginationParams,
        unread_only: bool,
    ) -> NotificationPage:
        items = await self.notifications.list_for_user(
            user_id=user.id,
            unread_only=unread_only,
            limit=page.limit,
            offset=page.skip,
        )
        unread = await self.notifications.count_unread(user.id)
        return NotificationPage(
            items=[NotificationResponse.model_validate(item) for item in items],
            total=len(items),
            unread=unread,
            skip=page.skip,
            limit=page.limit,
        )

    async def mark_read(
        self, notification_id: int, user: User
    ) -> NotificationResponse:
        notification = await self.notifications.get(notification_id)
        if notification is None or notification.user_id != user.id:
            raise NotFoundError("La notificación", notification_id)
        if notification.read_at is None:
            notification.read_at = func.now()
            await self.notifications.db.commit()
            await self.notifications.db.refresh(notification, ["read_at"])
        return NotificationResponse.model_validate(notification)
