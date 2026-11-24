"""app/services/auth_service.py
Registro, login, refresh y logout con rotación de refresh tokens.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.exceptions import PulseError, raise_duplicate
from app.models import User, UserRole
from app.repositories.refresh_token_repo import RefreshTokenRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth import Token
from app.schemas.user import UserRegister
from app.security import (
    ACCESS,
    REFRESH,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


def _sha256(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(
        self, users: UserRepository, refresh_tokens: RefreshTokenRepository
    ) -> None:
        self.users = users
        self.refresh_tokens = refresh_tokens

    async def register(self, data: UserRegister) -> User:
        if await self.users.get_by_email(str(data.email)):
            raise PulseError(409, "Email already registered")
        if await self.users.get_by_username(data.username):
            raise PulseError(409, "Username already taken")
        try:
            user = await self.users.create(
                username=data.username,
                email=str(data.email),
                hashed_password=hash_password(data.password),
                role=UserRole.reader,
            )
            await self.users.db.commit()
        except IntegrityError as exc:
            await self.users.db.rollback()
            raise raise_duplicate(str(exc.orig)) from exc
        return user

    async def login(self, email: str, password: str) -> Token:
        user = await self.users.get_by_email(email)
        if (
            user is None
            or not user.is_active
            or not verify_password(password, user.hashed_password)
        ):
            raise PulseError(401, "Invalid credentials")

        access_token = create_token(user.id, ACCESS)
        refresh_token = create_token(user.id, REFRESH)
        await self.refresh_tokens.create(
            user_id=user.id,
            jti=_sha256(refresh_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        await self.users.db.commit()
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh(self, refresh_token: str) -> Token:
        payload = decode_token(refresh_token, REFRESH)
        stored = await self.refresh_tokens.get_by_hash(_sha256(refresh_token))
        if (
            stored is None
            or stored.revoked_at is not None
            or stored.expires_at < datetime.now(timezone.utc)
        ):
            raise PulseError(401, "Invalid refresh token")

        user = await self.users.get_by_id(int(payload["sub"]))
        if user is None or not user.is_active:
            raise PulseError(401, "Invalid refresh token")

        await self.refresh_tokens.revoke(stored)
        access_token = create_token(user.id, ACCESS)
        new_refresh_token = create_token(user.id, REFRESH)
        await self.refresh_tokens.create(
            user_id=user.id,
            jti=_sha256(new_refresh_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        await self.users.db.commit()
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, refresh_token: str) -> None:
        stored = await self.refresh_tokens.get_by_hash(_sha256(refresh_token))
        if stored is not None and stored.revoked_at is None:
            await self.refresh_tokens.revoke(stored)
            await self.users.db.commit()
