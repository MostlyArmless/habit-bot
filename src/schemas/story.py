"""Story schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class StoryBase(BaseModel):
    """Base story schema."""

    story_text: str


class StoryCreate(StoryBase):
    """Schema for creating a story."""

    user_id: int


class Story(StoryBase):
    """Schema for story output."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    feedback: dict[str, Any] | None = None
    timestamp: datetime
    processing_status: str
    processing_attempts: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
