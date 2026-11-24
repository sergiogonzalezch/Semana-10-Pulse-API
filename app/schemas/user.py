"""app/schemas/user.py
Schemas de usuarios y registro público.
"""
from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,50}$")


class Password(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.reader

    @field_validator("username")
    @classmethod
    def valid_username(cls, v: str) -> str:
        if not USERNAME_PATTERN.fullmatch(v):
            raise ValueError("username must contain only letters, digits and underscores")
        return v


class UserRegister(UserCreate):
    """Registro público: el rol siempre es reader."""

    role: UserRole = UserRole.reader


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
