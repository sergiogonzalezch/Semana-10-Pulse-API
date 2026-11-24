"""app/schemas/post.py
Schemas de posts con reglas de status, relaciones y paginación.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.models.post import PostStatus
from app.schemas.category import CategoryResponse
from app.schemas.tag import TagSummary
from app.schemas.user import UserResponse

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class PostCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    slug: str = Field(min_length=3, max_length=200, pattern=SLUG_PATTERN)
    body: str = Field(min_length=10)
    excerpt: str | None = Field(default=None, max_length=300)
    status: PostStatus = PostStatus.draft
    published_at: datetime | None = None
    category_id: int | None = None
    tag_ids: list[int] = Field(default_factory=list)

    @field_validator("published_at")
    @classmethod
    def published_needs_status(
        cls, v: datetime | None, info: ValidationInfo
    ) -> datetime | None:
        if v is not None and info.data.get("status") != PostStatus.published:
            raise ValueError("published_at requires status='published'")
        return v


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    slug: str | None = Field(default=None, min_length=3, max_length=200, pattern=SLUG_PATTERN)
    body: str | None = Field(default=None, min_length=10)
    excerpt: str | None = Field(default=None, max_length=300)
    status: PostStatus | None = None
    published_at: datetime | None = None
    category_id: int | None = None
    tag_ids: list[int] | None = None


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    body: str
    excerpt: str | None
    status: PostStatus
    published_at: datetime | None
    views_count: int
    created_at: datetime
    updated_at: datetime
    author: UserResponse
    category: CategoryResponse | None
    tags: list[TagSummary]


class PostPage(BaseModel):
    items: list[PostResponse]
    total: int
    limit: int
    offset: int
