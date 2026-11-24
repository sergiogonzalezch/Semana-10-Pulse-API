"""app/routers/auth.py
Registro, login, refresh y logout.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.dependencies import get_auth_service
from app.schemas.auth import RefreshRequest, Token
from app.schemas.user import UserRegister
from app.services.auth_service import AuthService

# Todas las rutas de este archivo bajo /auth; el /api/v1 lo pone api_router (app/api.py)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    await service.register(data)
    return {"detail": "User registered"}


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
