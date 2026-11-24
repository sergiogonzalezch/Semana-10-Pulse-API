"""app/schemas/auth.py
Schemas de login, refresh y respuesta de tokens.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10)
