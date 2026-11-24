"""app/routers/comments.py
Endpoints de comentarios y aviso en tiempo real al autor del post.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import (
    get_comment_service,
    get_current_user,
    get_optional_user,
    pagination,
)
from app.models import Comment, User
from app.realtime import manager
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from app.schemas.notification import NotificationResponse
from app.services.comment_service import CommentService

router = APIRouter(tags=["comments"])

NOT_FOUND = {status.HTTP_404_NOT_FOUND: {"description": "No existe"}}
AUTH = {
    status.HTTP_401_UNAUTHORIZED: {
        "description": "Falta el token, es inválido o venció"
    }
}


@router.get("/comments", response_model=list[CommentResponse], responses=NOT_FOUND)
async def list_comments(
    post_id: int = Query(ge=1),
    service: CommentService = Depends(get_comment_service),
    page: tuple[int, int] = Depends(pagination),
    current_user: User | None = Depends(get_optional_user),
) -> list[Comment]:
    limit, offset = page
    return await service.list_for_post(
        post_id=post_id,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={**AUTH, **NOT_FOUND},
)
async def create_comment(
    post_id: int,
    data: CommentCreate,
    service: CommentService = Depends(get_comment_service),
    current_user: User = Depends(get_current_user),
) -> Comment:
    comment, notification = await service.create(post_id, data, current_user)
    if notification is not None:
        await manager.send_to_user(
            notification.user_id,
            {
                "type": "notification",
                "data": NotificationResponse.model_validate(notification).model_dump(
                    mode="json"
                ),
            },
        )
    return comment


@router.patch(
    "/comments/{comment_id}",
    response_model=CommentResponse,
    responses={**AUTH, **NOT_FOUND},
)
async def update_comment(
    comment_id: int,
    data: CommentUpdate,
    service: CommentService = Depends(get_comment_service),
    current_user: User = Depends(get_current_user),
) -> Comment:
    return await service.update(comment_id, data, current_user)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**AUTH, **NOT_FOUND},
)
async def delete_comment(
    comment_id: int,
    service: CommentService = Depends(get_comment_service),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.delete(comment_id, current_user)
