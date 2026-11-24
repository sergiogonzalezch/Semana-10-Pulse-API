"""app/dependencies.py
Factorías de servicios, usuario actual, roles, paginación y filtros.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import PulseError
from app.models import PostStatus, User, UserRole
from app.repositories.category_repo import CategoryRepository
from app.repositories.comment_repo import CommentRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.post_repo import PostRepository
from app.repositories.refresh_token_repo import RefreshTokenRepository
from app.repositories.tag_repo import TagRepository
from app.repositories.user_repo import UserRepository
from app.security import ACCESS, decode_token
from app.services.auth_service import AuthService
from app.services.category_service import CategoryService
from app.services.comment_service import CommentService
from app.services.notification_service import NotificationService
from app.services.post_service import PostService
from app.services.user_service import UserService


@dataclass
class PaginationParams:
    skip: int = Query(default=0, ge=0)
    limit: int = Query(default=20, ge=1, le=100)


async def get_user_repository(
    db: AsyncSession = Depends(get_db),
) -> UserRepository:
    return UserRepository(db)


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db), RefreshTokenRepository(db))


async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))


async def get_category_service(
    db: AsyncSession = Depends(get_db),
) -> CategoryService:
    return CategoryService(CategoryRepository(db))


async def get_post_service(db: AsyncSession = Depends(get_db)) -> PostService:
    return PostService(
        PostRepository(db),
        TagRepository(db),
        CategoryRepository(db),
    )


def get_comment_service(
    db: AsyncSession = Depends(get_db),
) -> CommentService:
    return CommentService(
        CommentRepository(db),
        PostRepository(db),
        NotificationRepository(db),
    )


def get_notification_service(
    db: AsyncSession = Depends(get_db),
) -> NotificationService:
    return NotificationService(NotificationRepository(db))


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    return token or None


async def get_current_user(
    authorization: str | None = Header(default=None),
    users: UserRepository = Depends(get_user_repository),
) -> User:
    token = _bearer_token(authorization)
    if token is None:
        raise PulseError(401, "Missing bearer token")
    try:
        payload = decode_token(token, ACCESS)
    except jwt.InvalidTokenError as exc:
        raise PulseError(401, "Invalid access token") from exc
    user = await users.get_by_id(int(payload["sub"]))
    if user is None or not user.is_active:
        raise PulseError(401, "Inactive user")
    return user


async def get_optional_user(
    request: Request,
    users: UserRepository = Depends(get_user_repository),
) -> User | None:
    token = _bearer_token(request.headers.get("Authorization"))
    if token is None:
        return None
    try:
        payload = decode_token(token, ACCESS)
    except jwt.InvalidTokenError:
        return None
    user = await users.get_by_id(int(payload["sub"]))
    if user is None or not user.is_active:
        return None
    return user


def require_role(
    *roles: UserRole,
) -> Callable[[User], Awaitable[User]]:
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise PulseError(403, "Not enough permissions")
        return user

    return checker


def pagination(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> tuple[int, int]:
    return limit, offset


def post_filters(
    status: PostStatus | None = Query(default=None),
    author_id: int | None = Query(default=None),
    category_id: int | None = Query(default=None),
    tag_id: int | None = Query(default=None),
) -> dict[str, object]:
    return {
        "status": status,
        "author_id": author_id,
        "category_id": category_id,
        "tag_id": tag_id,
    }
