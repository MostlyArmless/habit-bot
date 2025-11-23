"""Category schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CategoryBase(BaseModel):
    """Base category schema."""

    name: str
    description: str | None = None
    frequency_per_day: int = 4


class CategoryCreate(CategoryBase):
    """Schema for creating a category."""

    pass


class Category(CategoryBase):
    """Schema for category response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
