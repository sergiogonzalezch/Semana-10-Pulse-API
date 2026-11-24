"""app/schemas/tag.py
Schemas de tags.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TagSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
