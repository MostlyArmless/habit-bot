"""Prompt schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class PromptBase(BaseModel):
    """Base prompt schema."""

    scheduled_time: datetime
    questions: dict[str, Any]
    categories: list[str] | None = None


class PromptCreate(PromptBase):
    """Schema for creating a prompt."""

    user_id: int


class PromptUpdate(BaseModel):
    """Schema for updating a prompt."""

    status: str | None = None
    sent_time: datetime | None = None


class Prompt(PromptBase):
    """Schema for prompt response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    sent_time: datetime | None = None
    status: str
    created_at: datetime


class PromptWithResponses(Prompt):
    """Prompt with its responses."""

    responses: list["ResponseSummary"] = []


# Import here to avoid circular imports
from src.schemas.response import ResponseSummary  # noqa: E402

PromptWithResponses.model_rebuild()
