"""app/repositories/tag_repo.py
Acceso a tags. Flush, nunca commit.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tag


class TagRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, tag_id: int) -> Tag | None:
        return await self.db.get(Tag, tag_id)

    async def get_by_ids(self, tag_ids: list[int]) -> list[Tag]:
        if not tag_ids:
            return []
        result = await self.db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> Tag | None:
        result = await self.db.execute(select(Tag).where(Tag.slug == slug))
        return result.scalar_one_or_none()

    async def list(self, limit: int, offset: int) -> list[Tag]:
        result = await self.db.execute(
            select(Tag).order_by(Tag.name).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def create(self, *, name: str, slug: str) -> Tag:
        tag = Tag(name=name, slug=slug)
        self.db.add(tag)
        await self.db.flush()
        return tag
