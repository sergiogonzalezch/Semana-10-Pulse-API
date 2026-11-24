"""app/services/comment_service.py
Comentarios con control de visibilidad, autoría y notificación al autor del post.
"""
from __future__ import annotations

from app.exceptions import NotFoundError, PulseError
from app.models import Comment, Notification, Post, User, UserRole
from app.permissions import can_view_post
from app.repositories.comment_repo import CommentRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.post_repo import PostRepository
from app.schemas.comment import CommentCreate, CommentUpdate


class CommentService:
    def __init__(
        self,
        comments: CommentRepository,
        posts: PostRepository,
        notifications: NotificationRepository,
    ) -> None:
        self.comments = comments
        self.posts = posts
        self.notifications = notifications

    async def _require_visible_post(
        self, post_id: int, current_user: User | None
    ) -> Post:
        post = await self.posts.get_by_id(post_id)
        if post is None or not can_view_post(post, current_user):
            raise NotFoundError("El post", post_id)
        return post

    async def list_for_post(
        self,
        post_id: int,
        current_user: User | None,
        limit: int,
        offset: int,
    ) -> list[Comment]:
        await self._require_visible_post(post_id, current_user)
        return await self.comments.list_for_post(
            post_id=post_id, limit=limit, offset=offset
        )

    async def create(
        self, post_id: int, data: CommentCreate, author: User
    ) -> tuple[Comment, Notification | None]:
        post = await self._require_visible_post(post_id, author)
        comment = await self.comments.create(
            body=data.body,
            author_id=author.id,
            post_id=post.id,
        )
        notification = None
        if post.author_id != author.id:
            notification = await self.notifications.add(
                Notification(
                    user_id=post.author_id,
                    actor_id=author.id,
                    post_id=post.id,
                    comment_id=comment.id,
                    kind="new_comment",
                )
            )
        await self.comments.db.commit()
        if notification is not None:
            notification = await self.notifications.get(notification.id)
        return comment, notification

    async def get(self, comment_id: int) -> Comment:
        comment = await self.comments.get_by_id(comment_id)
        if comment is None:
            raise PulseError(404, "Comment not found")
        return comment

    async def update(
        self, comment_id: int, data: CommentUpdate, current_user: User
    ) -> Comment:
        comment = await self.get(comment_id)
        if comment.author_id != current_user.id and current_user.role != UserRole.admin:
            raise PulseError(403, "Not enough permissions")
        comment.body = data.body
        comment.is_edited = True
        await self.comments.db.commit()
        return comment

    async def delete(self, comment_id: int, current_user: User) -> None:
        comment = await self.get(comment_id)
        if comment.author_id != current_user.id and current_user.role != UserRole.admin:
            raise PulseError(403, "Not enough permissions")
        await self.comments.db.delete(comment)
        await self.comments.db.commit()
