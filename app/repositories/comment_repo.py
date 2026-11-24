"""app/repositories/comment_repo.py
Acceso a comments. Flush, nunca commit.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Comment


class CommentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, comment_id: int) -> Comment | None:
        result = await self.db.execute(
            select(Comment)
            .where(Comment.id == comment_id)
            .options(selectinload(Comment.author))
        )
        return result.scalar_one_or_none()

    async def list_for_post(
        self, post_id: int, limit: int, offset: int
    ) -> list[Comment]:
        result = await self.db.execute(
            select(Comment)
            .where(Comment.post_id == post_id)
            .order_by(Comment.created_at, Comment.id)
            .limit(limit)
            .offset(offset)
            .options(selectinload(Comment.author))
        )
        return list(result.scalars().all())

    async def create(self, *, body: str, author_id: int, post_id: int) -> Comment:
        comment = Comment(body=body, author_id=author_id, post_id=post_id)
        self.db.add(comment)
        await self.db.flush()
        return comment
