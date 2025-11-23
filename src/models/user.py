"""User model."""

from datetime import datetime

from sqlalchemy import String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class User(Base):
    """User model for storing user profiles and preferences."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    wake_time: Mapped[datetime | None] = mapped_column(Time, nullable=True)
    sleep_time: Mapped[datetime | None] = mapped_column(Time, nullable=True)
    screens_off_time: Mapped[datetime | None] = mapped_column(Time, nullable=True)
    bed_time: Mapped[datetime | None] = mapped_column(Time, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    prompts: Mapped[list["Prompt"]] = relationship(back_populates="user")  # noqa: F821
    responses: Mapped[list["Response"]] = relationship(back_populates="user")  # noqa: F821
    behaviors: Mapped[list["Behavior"]] = relationship(back_populates="user")  # noqa: F821
    outcomes: Mapped[list["Outcome"]] = relationship(back_populates="user")  # noqa: F821
    garmin_data: Mapped[list["GarminData"]] = relationship(back_populates="user")  # noqa: F821
    calendar_events: Mapped[list["CalendarEvent"]] = relationship(  # noqa: F821
        back_populates="user"
    )
    correlations: Mapped[list["Correlation"]] = relationship(back_populates="user")  # noqa: F821
    insights: Mapped[list["Insight"]] = relationship(back_populates="user")  # noqa: F821
    historical_gaps: Mapped[list["HistoricalGap"]] = relationship(  # noqa: F821
        back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.name}')>"
