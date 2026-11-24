"""app/services/user_service.py
Altas y consultas de usuarios.
"""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.exceptions import PulseError, raise_duplicate
from app.models import User, UserRole
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate
from app.security import hash_password


class UserService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    async def get(self, user_id: int) -> User:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise PulseError(404, "User not found")
        return user

    async def list(self, limit: int, offset: int) -> list[User]:
        return await self.users.list(limit=limit, offset=offset)

    async def create(self, data: UserCreate) -> User:
        if await self.users.get_by_email(str(data.email)):
            raise PulseError(409, "Email already registered")
        if await self.users.get_by_username(data.username):
            raise PulseError(409, "Username already taken")
        try:
            user = await self.users.create(
                username=data.username,
                email=str(data.email),
                hashed_password=hash_password(data.password),
                role=data.role or UserRole.reader,
            )
            await self.users.db.commit()
            return user
        except IntegrityError as exc:
            await self.users.db.rollback()
            raise raise_duplicate(str(exc.orig)) from exc
