"""User schemas."""

from datetime import datetime, time

from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    """Base user schema."""

    name: str
    timezone: str = "UTC"
    wake_time: time | None = None
    sleep_time: time | None = None
    screens_off_time: time | None = None
    bed_time: time | None = None


class UserCreate(UserBase):
    """Schema for creating a user."""

    pass


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    name: str | None = None
    timezone: str | None = None
    wake_time: time | None = None
    sleep_time: time | None = None
    screens_off_time: time | None = None
    bed_time: time | None = None


class User(UserBase):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
