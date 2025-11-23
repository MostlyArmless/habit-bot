"""Response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ResponseBase(BaseModel):
    """Base response schema."""

    question_text: str
    response_text: str
    category: str | None = None


class ResponseCreate(ResponseBase):
    """Schema for creating a response."""

    prompt_id: int
    user_id: int


class Response(ResponseBase):
    """Schema for response output."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    prompt_id: int
    user_id: int
    response_structured: dict[str, Any] | None = None
    timestamp: datetime
    processing_status: str
    processing_attempts: int


class ResponseSummary(BaseModel):
    """Summarized response for embedding in other schemas."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    response_text: str
    category: str | None = None
    timestamp: datetime
    processing_status: str
