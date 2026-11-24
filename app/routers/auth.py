"""app/routers/auth.py
Registro, login, refresh y logout.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.dependencies import get_auth_service
from app.schemas.auth import RefreshRequest, Token
from app.schemas.user import UserRegister, UserResponse
from app.services.auth_service import AuthService
from app.tasks import log_event

# Todas las rutas de este archivo bajo /auth; el /api/v1 lo pone api_router (app/api.py)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: UserRegister,
    background_tasks: BackgroundTasks,
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Crea una cuenta con rol reader; el evento de analytics corre después de responder."""
    user = await service.register(data)
    background_tasks.add_task(
        log_event, "user_registered", {"user_id": user.id, "username": user.username}
    )
    return user


@router.post("/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
) -> Token:
    return await service.login(form.username, form.password)


@router.post("/refresh", response_model=Token)
async def refresh(
    data: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> Token:
    return await service.refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> None:
    await service.logout(data.refresh_token)
