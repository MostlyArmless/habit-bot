"""Response model."""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.mixins import SoftDeleteMixin, TimestampMixin


class ProcessingStatus(str, Enum):
    """Processing status of a response."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Response(Base, TimestampMixin, SoftDeleteMixin):
    """Response model for storing user responses to prompts."""

    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    prompt_id: Mapped[int] = mapped_column(ForeignKey("prompts.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_structured: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Keep timestamp for backwards compatibility, but prefer created_at
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    processing_status: Mapped[str] = mapped_column(
        String(50), default=ProcessingStatus.PENDING.value
    )
    processing_attempts: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    prompt: Mapped["Prompt"] = relationship(back_populates="responses")  # noqa: F821
    user: Mapped["User"] = relationship(back_populates="responses")  # noqa: F821
    behaviors: Mapped[list["Behavior"]] = relationship(back_populates="response")  # noqa: F821
    outcomes: Mapped[list["Outcome"]] = relationship(back_populates="response")  # noqa: F821

    __table_args__ = (
        Index("idx_responses_timestamp", "timestamp"),
        Index("idx_responses_category", "category"),
        Index("idx_responses_prompt_id", "prompt_id"),
    )

    def __repr__(self) -> str:
        return f"<Response(id={self.id}, processing_status='{self.processing_status}')>"
