"""app/schemas/notification.py
Schemas de notificaciones.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field

from app.schemas.user import UserSummary


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    actor_id: int
    post_id: int
    comment_id: int
    kind: str
    read_at: datetime | None
    created_at: datetime
    actor: UserSummary

    @computed_field
    @property
    def message(self) -> str:
        if self.kind == "new_comment":
            return f"{self.actor.username} comentó tu post"
        return "Nueva notificación"


class NotificationPage(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread: int
    skip: int
    limit: int
