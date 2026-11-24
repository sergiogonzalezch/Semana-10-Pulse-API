"""app/repositories/user_repo.py
Acceso a users. Flush, nunca commit.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.db.get(User, user_id)

    async def get(self, user_id: int) -> User | None:
        return await self.get_by_id(user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def list(self, limit: int, offset: int) -> list[User]:
        result = await self.db.execute(
            select(User).order_by(User.id).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def create(
        self,
        *,
        username: str,
        email: str,
        hashed_password: str,
        role: UserRole = UserRole.reader,
    ) -> User:
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        return user
