"""Outcome model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Outcome(Base):
    """Outcome model for storing measured outcomes (mood, energy, etc.)."""

    __tablename__ = "outcomes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    response_id: Mapped[int | None] = mapped_column(ForeignKey("responses.id"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    outcome_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    response: Mapped["Response | None"] = relationship(back_populates="outcomes")  # noqa: F821
    user: Mapped["User"] = relationship(back_populates="outcomes")  # noqa: F821

    __table_args__ = (
        Index("idx_outcomes_timestamp", "timestamp"),
        Index("idx_outcomes_outcome_type", "outcome_type"),
    )

    def __repr__(self) -> str:
        return f"<Outcome(id={self.id}, outcome_type='{self.outcome_type}')>"
