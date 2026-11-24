"""app/routers/categories.py
Endpoints de categorías.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.dependencies import get_category_service, pagination, require_role
from app.models import Category, User, UserRole
from app.schemas.category import CategoryCreate, CategoryResponse
from app.services.category_service import CategoryService

# Todas las rutas bajo /categories; el /api/v1 lo pone api_router
router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    service: CategoryService = Depends(get_category_service),
    page: tuple[int, int] = Depends(pagination),
) -> list[Category]:
    limit, offset = page
    return await service.list(limit=limit, offset=offset)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
) -> Category:
    return await service.get(category_id)


@router.post(
    "", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED
)
async def create_category(
    data: CategoryCreate,
    service: CategoryService = Depends(get_category_service),
    _: User = Depends(require_role(UserRole.admin)),
) -> Category:
    return await service.create(data)
