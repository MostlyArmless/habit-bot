"""Reminder model for scheduled check-ins sent to users."""

from datetime import datetime
from enum import Enum

from sqlalchemy import ARRAY, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class ReminderStatus(str, Enum):
    """Status of a reminder."""

    SCHEDULED = "scheduled"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    MISSED = "missed"


class Reminder(Base):
    """Reminder model for storing scheduled check-in notifications.

    Reminders are the notifications sent to users throughout the day
    that they must respond to via a questionnaire.
    """

    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    scheduled_time: Mapped[datetime] = mapped_column(nullable=False)
    sent_time: Mapped[datetime | None] = mapped_column(nullable=True)
    questions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=ReminderStatus.SCHEDULED.value)
    categories: Mapped[list[str] | None] = mapped_column(ARRAY(String(100)), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="reminders")  # noqa: F821
    responses: Mapped[list["Response"]] = relationship(back_populates="reminder")  # noqa: F821

    __table_args__ = (
        Index("idx_reminders_scheduled_time", "scheduled_time"),
        Index("idx_reminders_status", "status"),
        Index("idx_reminders_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<Reminder(id={self.id}, status='{self.status}')>"
