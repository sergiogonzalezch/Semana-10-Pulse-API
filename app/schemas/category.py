"""app/schemas/category.py
Schemas de categorías.
"""
from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("slug")
    @classmethod
    def valid_slug(cls, v: str) -> str:
        if not SLUG_PATTERN.fullmatch(v):
            raise ValueError("slug must be lowercase kebab-case")
        return v


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
