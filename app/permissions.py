"""app/permissions.py
Reglas de acceso reutilizables.
"""
from __future__ import annotations

from fastapi import HTTPException

from app.models import Post, User


def can_view_post(post: Post, current_user: User | None) -> bool:
    """Publicado es público; borrador solo autor o admin."""
    if post.status == "published":
        return True
    if current_user is None:
        return False
    return current_user.role == "admin" or current_user.id == post.author_id


def ensure_owner_or_admin(post: Post, current_user: User) -> None:
    """El autor o un admin pueden modificar; si no, 403."""
    if post.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
