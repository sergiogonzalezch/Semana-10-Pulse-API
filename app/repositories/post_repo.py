"""app/repositories/post_repo.py
Acceso a posts. Flush, nunca commit.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

# Row es una fila de resultados
from sqlalchemy import Row, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Post, PostStatus, User, post_tags


class PostRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _with_relations(self, stmt):
        return stmt.options(
            selectinload(Post.author),
            selectinload(Post.category),
            selectinload(Post.tags),
        )

    async def get_by_id(self, post_id: int) -> Post | None:
        result = await self.db.execute(
            self._with_relations(select(Post).where(Post.id == post_id))
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Post | None:
        result = await self.db.execute(
            self._with_relations(select(Post).where(Post.slug == slug))
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        status: PostStatus | None = None,
        author_id: int | None = None,
        category_id: int | None = None,
        tag_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Post], int]:
        stmt = self._with_relations(select(Post))
        count_stmt = select(func.count()).select_from(Post)

        if status is not None:
            stmt = stmt.where(Post.status == status)
            count_stmt = count_stmt.where(Post.status == status)
        if author_id is not None:
            stmt = stmt.where(Post.author_id == author_id)
            count_stmt = count_stmt.where(Post.author_id == author_id)
        if category_id is not None:
            stmt = stmt.where(Post.category_id == category_id)
            count_stmt = count_stmt.where(Post.category_id == category_id)
        if tag_id is not None:
            stmt = stmt.join(post_tags).where(post_tags.c.tag_id == tag_id)
            count_stmt = count_stmt.join(post_tags).where(post_tags.c.tag_id == tag_id)

        total = int((await self.db.execute(count_stmt)).scalar_one())
        stmt = (
            stmt.order_by(Post.published_at.desc().nullslast(), Post.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all()), total

    async def list_by_author(
        self, author_id: int, limit: int, offset: int
    ) -> tuple[list[Post], int]:
        return await self.list(author_id=author_id, limit=limit, offset=offset)

    async def create(
        self,
        *,
        title: str,
        slug: str,
        body: str,
        excerpt: str | None,
        status: PostStatus,
        published_at: datetime | None,
        author_id: int,
        category_id: int | None,
    ) -> Post:
        post = Post(
            title=title,
            slug=slug,
            body=body,
            excerpt=excerpt,
            status=status,
            published_at=published_at,
            author_id=author_id,
            category_id=category_id,
        )
        self.db.add(post)
        await self.db.flush()
        return post

    async def save(self, post: Post) -> Post:
        self.db.add(post)
        await self.db.flush()
        return post

    async def stream_for_export(self, drafts_of: int | None) -> AsyncIterator[Row]:
        """Las filas del export, de a poco: un cursor del lado del servidor, no una lista."""
        # Solo las columnas del CSV, con el username del autor (un JOIN, sin objetos Post)
        stmt = (
            select(
                Post.id,
                Post.slug,
                Post.title,
                Post.status,
                Post.published_at,
                User.username.label("author"),
            )
            .join(Post.author)
            .order_by(Post.id)
            # PostgreSQL las manda de 100 en 100; Python nunca tiene todas a la vez
            .execution_options(yield_per=100)
        )
        # La misma regla de visibilidad que el listado: publicados + tus borradores
        if drafts_of is not None:
            stmt = stmt.where(or_(Post.status == PostStatus.published, Post.author_id == drafts_of))
        result = await self.db.stream(stmt)
        async for row in result:
            yield row
