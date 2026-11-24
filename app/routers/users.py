"""app/routers/users.py
Endpoints de usuarios.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.dependencies import (
    get_current_user,
    get_user_service,
    pagination,
    require_role,
)
from app.exceptions import PulseError
from app.models import User, UserRole
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService

# El /api/v1 lo pone api_router
router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("", response_model=list[UserResponse])
async def list_users(
    service: UserService = Depends(get_user_service),
    page: tuple[int, int] = Depends(pagination),
    _: User = Depends(require_role(UserRole.admin)),
) -> list[User]:
    limit, offset = page
    return await service.list(limit=limit, offset=offset)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    service: UserService = Depends(get_user_service),
    _: User = Depends(require_role(UserRole.admin)),
) -> User:
    return await service.create(data)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.admin and current_user.id != user_id:
        raise PulseError(403, "Not enough permissions")
    return await service.get(user_id)
