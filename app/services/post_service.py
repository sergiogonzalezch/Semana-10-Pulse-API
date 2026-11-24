"""app/services/post_service.py
Reglas de posts: visibilidad de borradores, autoría y relaciones.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.exceptions import PulseError, raise_duplicate
from app.models import Post, PostStatus, User, UserRole
from app.permissions import can_view_post, ensure_owner_or_admin
from app.repositories.category_repo import CategoryRepository
from app.repositories.post_repo import PostRepository
from app.repositories.tag_repo import TagRepository
from app.schemas.post import PostCreate, PostUpdate


class PostService:
    def __init__(
        self,
        posts: PostRepository,
        tags: TagRepository,
        categories: CategoryRepository,
    ) -> None:
        self.posts = posts
        self.tags = tags
        self.categories = categories

    async def get(self, post_id: int, current_user: User | None) -> Post:
        post = await self.posts.get_by_id(post_id)
        if post is None or not can_view_post(post, current_user):
            raise PulseError(404, "Post not found")
        return post

    async def get_by_slug(self, slug: str, current_user: User | None) -> Post:
        post = await self.posts.get_by_slug(slug)
        if post is None or not can_view_post(post, current_user):
            raise PulseError(404, "Post not found")
        post.views_count += 1
        await self.posts.db.commit()
        return post

    async def list(
        self,
        *,
        status: PostStatus | None = None,
        author_id: int | None = None,
        category_id: int | None = None,
        tag_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
        current_user: User | None = None,
    ) -> tuple[list[Post], int]:
        privileged = current_user is not None and current_user.role in (
            UserRole.admin,
            UserRole.author,
        )
        if not privileged:
            if status is not None and status != PostStatus.published:
                raise PulseError(403, "Cannot list non-published posts")
            status = PostStatus.published
        return await self.posts.list(
            status=status,
            author_id=author_id,
            category_id=category_id,
            tag_id=tag_id,
            limit=limit,
            offset=offset,
        )

    async def create(self, data: PostCreate, current_user: User) -> Post:
        if current_user.role not in (UserRole.admin, UserRole.author):
            raise PulseError(403, "Only authors can create posts")
        if await self.posts.get_by_slug(data.slug):
            raise PulseError(409, "Slug already exists")
        if data.category_id is not None:
            if await self.categories.get_by_id(data.category_id) is None:
                raise PulseError(404, "Category not found")

        tag_ids = list(dict.fromkeys(data.tag_ids))
        tags = await self.tags.get_by_ids(tag_ids)
        if len(tags) != len(tag_ids):
            raise PulseError(404, "Tag not found")

        published_at = data.published_at
        if data.status == PostStatus.published and published_at is None:
            published_at = datetime.now(timezone.utc)

        try:
            post = await self.posts.create(
                title=data.title,
                slug=data.slug,
                body=data.body,
                excerpt=data.excerpt,
                status=data.status,
                published_at=published_at,
                author_id=current_user.id,
                category_id=data.category_id,
            )
            post.tags = tags
            await self.posts.db.commit()
            return post
        except IntegrityError as exc:
            await self.posts.db.rollback()
            raise raise_duplicate(str(exc.orig)) from exc

    async def update(
        self, post_id: int, data: PostUpdate, current_user: User
    ) -> Post:
        post = await self.posts.get_by_id(post_id)
        if post is None:
            raise PulseError(404, "Post not found")
        ensure_owner_or_admin(post, current_user)

        payload = data.model_dump(exclude_unset=True)
        tag_ids = payload.pop("tag_ids", None)
        category_id = payload.get("category_id")
        if category_id is not None:
            if await self.categories.get_by_id(category_id) is None:
                raise PulseError(404, "Category not found")

        if tag_ids is not None:
            unique_tag_ids = list(dict.fromkeys(tag_ids))
            tags = await self.tags.get_by_ids(unique_tag_ids)
            if len(tags) != len(unique_tag_ids):
                raise PulseError(404, "Tag not found")
            post.tags = tags

        for key, value in payload.items():
            setattr(post, key, value)

        if post.status == PostStatus.published and post.published_at is None:
            post.published_at = datetime.now(timezone.utc)

        try:
            await self.posts.db.commit()
            return post
        except IntegrityError as exc:
            await self.posts.db.rollback()
            raise raise_duplicate(str(exc.orig)) from exc

    async def delete(self, post_id: int, current_user: User) -> None:
        post = await self.posts.get_by_id(post_id)
        if post is None:
            raise PulseError(404, "Post not found")
        ensure_owner_or_admin(post, current_user)
        await self.posts.db.delete(post)
        await self.posts.db.commit()
