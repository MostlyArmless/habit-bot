"""Reminder schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ReminderBase(BaseModel):
    """Base reminder schema."""

    scheduled_time: datetime
    questions: dict[str, Any]
    categories: list[str] | None = None


class ReminderCreate(ReminderBase):
    """Schema for creating a reminder."""

    user_id: int


class ReminderUpdate(BaseModel):
    """Schema for updating a reminder."""

    status: str | None = None
    sent_time: datetime | None = None


class Reminder(ReminderBase):
    """Schema for reminder response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    sent_time: datetime | None = None
    status: str
    created_at: datetime


class ReminderWithResponses(Reminder):
    """Reminder with its responses."""

    responses: list["ResponseSummary"] = []


# Import here to avoid circular imports
from src.schemas.response import ResponseSummary  # noqa: E402

ReminderWithResponses.model_rebuild()
