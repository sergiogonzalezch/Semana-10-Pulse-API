"""app/models/__init__.py
Importa los ocho modelos para que Base.metadata los conozca.
"""
from app.models.base import Base
from app.models.category import Category
from app.models.comment import Comment
from app.models.notification import Notification
from app.models.post import Post, PostStatus
from app.models.refresh_token import RefreshToken
from app.models.tag import Tag, post_tags
from app.models.user import User, UserRole

__all__ = [
    "Base",
    "Category",
    "Comment",
    "Notification",
    "Post",
    "PostStatus",
    "RefreshToken",
    "Tag",
    "User",
    "UserRole",
    "post_tags",
]
