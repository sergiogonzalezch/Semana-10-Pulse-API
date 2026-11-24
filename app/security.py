"""app/security.py
Hashing de contraseñas (pwdlib/bcrypt) y JWT (PyJWT): access y refresh.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

from app.config import settings

password_hash = PasswordHash([BcryptHasher()])

ACCESS = "access"
REFRESH = "refresh"


def hash_password(plain: str) -> str:
    """Devuelve un hash bcrypt listo para guardar en users.hashed_password."""
    return password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica una contraseña contra el hash almacenado."""
    return password_hash.verify(plain, hashed)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_token(subject: str | int, token_type: str) -> str:
    """Crea un JWT firmado con sub, type, iat, exp y jti."""
    now = _now()
    if token_type == ACCESS:
        expires = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    elif token_type == REFRESH:
        expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        raise ValueError(f"Unknown token type: {token_type}")
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": expires,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """Decodifica y exige que el tipo de token sea el esperado."""
    payload: dict[str, Any] = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"Expected {expected_type} token")
    return payload
