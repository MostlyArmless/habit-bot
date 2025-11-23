"""Behavior model."""

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Behavior(Base):
    """Behavior model for storing tracked behaviors."""

    __tablename__ = "behaviors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    response_id: Mapped[int | None] = mapped_column(ForeignKey("responses.id"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    behavior_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # survey, garmin, manual

    # Relationships
    response: Mapped["Response | None"] = relationship(back_populates="behaviors")  # noqa: F821
    user: Mapped["User"] = relationship(back_populates="behaviors")  # noqa: F821

    __table_args__ = (
        Index("idx_behaviors_timestamp", "timestamp"),
        Index("idx_behaviors_category", "category"),
        Index("idx_behaviors_behavior_type", "behavior_type"),
    )

    def __repr__(self) -> str:
        return f"<Behavior(id={self.id}, category='{self.category}')>"
