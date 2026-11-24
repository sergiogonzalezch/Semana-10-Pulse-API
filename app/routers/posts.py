"""app/routers/posts.py
Endpoints de posts con visibilidad por rol.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.dependencies import (
    get_current_user,
    get_optional_user,
    get_post_service,
    pagination,
    post_filters,
    require_role,
)
from app.models import Post, User, UserRole
from app.schemas.post import PostCreate, PostPage, PostResponse, PostUpdate
from app.services.post_service import PostService

# Todas las rutas bajo /posts; el /api/v1 lo pone api_router
router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_model=PostPage)
async def list_posts(
    service: PostService = Depends(get_post_service),
    filters: dict[str, object] = Depends(post_filters),
    page: tuple[int, int] = Depends(pagination),
    current_user: User | None = Depends(get_optional_user),
) -> PostPage:
    limit, offset = page
    items, total = await service.list(
        **filters,
        limit=limit,
        offset=offset,
        current_user=current_user,
    )
    return PostPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/slug/{slug}", response_model=PostResponse)
async def get_by_slug(
    slug: str,
    service: PostService = Depends(get_post_service),
    current_user: User | None = Depends(get_optional_user),
) -> Post:
    return await service.get_by_slug(slug, current_user)


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    service: PostService = Depends(get_post_service),
    current_user: User | None = Depends(get_optional_user),
) -> Post:
    return await service.get(post_id, current_user)


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    data: PostCreate,
    service: PostService = Depends(get_post_service),
    current_user: User = Depends(require_role(UserRole.author, UserRole.admin)),
) -> Post:
    return await service.create(data, current_user)


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    data: PostUpdate,
    service: PostService = Depends(get_post_service),
    current_user: User = Depends(get_current_user),
) -> Post:
    return await service.update(post_id, data, current_user)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    service: PostService = Depends(get_post_service),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.delete(post_id, current_user)
