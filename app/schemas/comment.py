"""app/schemas/comment.py
Schemas de comentarios.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserSummary


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class CommentUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    author_id: int
    author: UserSummary
    post_id: int
    is_edited: bool
    created_at: datetime
    updated_at: datetime
