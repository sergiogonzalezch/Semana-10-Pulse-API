"""app/services/category_service.py
Altas y consultas de categorías.
"""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.exceptions import PulseError, raise_duplicate
from app.models import Category
from app.repositories.category_repo import CategoryRepository
from app.schemas.category import CategoryCreate


class CategoryService:
    def __init__(self, categories: CategoryRepository) -> None:
        self.categories = categories

    async def get(self, category_id: int) -> Category:
        category = await self.categories.get_by_id(category_id)
        if category is None:
            raise PulseError(404, "Category not found")
        return category

    async def list(self, limit: int, offset: int) -> list[Category]:
        return await self.categories.list(limit=limit, offset=offset)

    async def create(self, data: CategoryCreate) -> Category:
        if await self.categories.get_by_slug(data.slug):
            raise PulseError(409, "Category slug already exists")
        try:
            category = await self.categories.create(
                name=data.name,
                slug=data.slug,
                description=data.description,
            )
            await self.categories.db.commit()
            return category
        except IntegrityError as exc:
            await self.categories.db.rollback()
            raise raise_duplicate(str(exc.orig)) from exc
