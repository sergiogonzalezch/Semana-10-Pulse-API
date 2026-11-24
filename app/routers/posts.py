"""app/routers/posts.py
Endpoints de posts con visibilidad por rol.
"""
from __future__ import annotations

# APIRouter, Depends, File, UploadFile y status de FastAPI
from fastapi import APIRouter, Depends, File, UploadFile, status
# FileResponse sirve un archivo del disco; StreamingResponse, un generator
from fastapi.responses import FileResponse, StreamingResponse

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

NOT_FOUND = {status.HTTP_404_NOT_FOUND: {"description": "No existe"}}
AUTH = {status.HTTP_401_UNAUTHORIZED: {"description": "Falta el token o no es válido"}}


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


# GET /posts/export: va ANTES de /{post_id}. Si fuera después, "export" llegaría a
# get_post como post_id y FastAPI respondería 422 (no es un entero).
@router.get(
    "/export",
    summary="Exportar los posts a CSV",
    response_class=StreamingResponse,
    responses={
        200: {"content": {"text/csv": {}}, "description": "El CSV, en streaming"}
    },
)
async def export_posts(
    viewer: User | None = Depends(get_optional_user),
    service: PostService = Depends(get_post_service),
) -> StreamingResponse:
    """Descarga un CSV con los posts que puedes ver. Se manda mientras se genera."""
    return StreamingResponse(
        service.export_csv(viewer),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="posts.csv"'},
    )


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
    """Borra el post y su imagen en disco (si tiene)."""
    await service.delete(post_id, current_user)


# POST /posts/{id}/image: subir (o reemplazar) la imagen; multipart/form-data, no JSON
@router.post(
    "/{post_id}/image",
    response_model=PostResponse,
    summary="Subir la imagen del post",
    responses={
        **NOT_FOUND,
        **AUTH,
        413: {"description": "Pasa de 5 MB"},
        415: {"description": "No es JPEG ni PNG"},
    },
)
async def upload_post_image(
    post_id: int,
    # El campo "file" del formulario; FastAPI necesita python-multipart para leerlo
    file: UploadFile = File(description="JPEG o PNG, hasta 5 MB"),
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
) -> Post:
    """Guarda la imagen del post (solo el autor o un admin) y borra la anterior."""
    return await service.set_image(post_id, file, current_user)


# GET /posts/{id}/image: la imagen, servida desde el disco
@router.get(
    "/{post_id}/image",
    response_class=FileResponse,
    summary="La imagen del post",
    responses={
        **NOT_FOUND,
        200: {"content": {"image/jpeg": {}, "image/png": {}}},
    },
)
async def get_post_image(
    post_id: int,
    viewer: User | None = Depends(get_optional_user),
    service: PostService = Depends(get_post_service),
) -> FileResponse:
    """Devuelve la imagen con su Content-Type (image/png o image/jpeg) y su tamaño."""
    # FileResponse lee el archivo en partes y adivina el tipo por la extensión
    return FileResponse(await service.get_image_path(post_id, viewer))
