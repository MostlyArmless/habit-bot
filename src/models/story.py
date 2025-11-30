"""Story model for daily storytelling practice."""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.mixins import SoftDeleteMixin, TimestampMixin


class StoryProcessingStatus(str, Enum):
    """Processing status of a story."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Story(Base, TimestampMixin, SoftDeleteMixin):
    """Story model for storing user's daily storytelling practice.

    This is separate from health tracking and focuses on developing
    storytelling skills with Toastmaster-style feedback.
    """

    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    story_text: Mapped[str] = mapped_column(Text, nullable=False)
    feedback: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    processing_status: Mapped[str] = mapped_column(
        String(50), default=StoryProcessingStatus.PENDING.value
    )
    processing_attempts: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="stories")  # noqa: F821

    __table_args__ = (
        Index("idx_stories_timestamp", "timestamp"),
        Index("idx_stories_user_id", "user_id"),
        Index("idx_stories_processing_status", "processing_status"),
    )

    def __repr__(self) -> str:
        return f"<Story(id={self.id}, user_id={self.user_id}, processing_status='{self.processing_status}')>"
