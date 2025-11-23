"""Calendar event model."""

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class CalendarEvent(Base):
    """CalendarEvent model for storing synced calendar events."""

    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(255), unique=True)  # Google Calendar event ID
    calendar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)  # busy, free, tentative
    can_interrupt: Mapped[bool] = mapped_column(Boolean, default=False)
    synced_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="calendar_events")  # noqa: F821

    __table_args__ = (
        Index("idx_calendar_events_start_time", "start_time"),
        Index("idx_calendar_events_end_time", "end_time"),
    )

    def __repr__(self) -> str:
        return f"<CalendarEvent(id={self.id}, title='{self.title}')>"
