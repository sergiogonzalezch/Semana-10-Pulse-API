"""app/repositories/category_repo.py
Acceso a categories. Flush, nunca commit.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category


class CategoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, category_id: int) -> Category | None:
        return await self.db.get(Category, category_id)

    async def get_by_slug(self, slug: str) -> Category | None:
        result = await self.db.execute(select(Category).where(Category.slug == slug))
        return result.scalar_one_or_none()

    async def list(self, limit: int, offset: int) -> list[Category]:
        result = await self.db.execute(
            select(Category).order_by(Category.name).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def create(
        self, *, name: str, slug: str, description: str | None
    ) -> Category:
        category = Category(name=name, slug=slug, description=description)
        self.db.add(category)
        await self.db.flush()
        return category
