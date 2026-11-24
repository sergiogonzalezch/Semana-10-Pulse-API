"""app/repositories/notification_repository.py
Acceso a notifications. Flush, nunca commit.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(self, notification: Notification) -> Notification:
        self.db.add(notification)
        await self.db.flush()
        return notification

    async def get(self, notification_id: int) -> Notification | None:
        result = await self.db.execute(
            select(Notification)
            .where(Notification.id == notification_id)
            .options(selectinload(Notification.actor))
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        *,
        user_id: int,
        unread_only: bool,
        limit: int,
        offset: int,
    ) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .options(selectinload(Notification.actor))
        )
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))
        stmt = (
            stmt.order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_unread(self, user_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
        return int((await self.db.scalar(stmt)) or 0)
