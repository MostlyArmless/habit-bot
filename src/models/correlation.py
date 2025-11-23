"""Correlation model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Correlation(Base):
    """Correlation model for storing discovered correlations between behaviors and outcomes."""

    __tablename__ = "correlations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    behavior_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    outcome_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_strength: Mapped[Decimal | None] = mapped_column(
        Numeric, nullable=True
    )  # -1 to 1
    confidence_level: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)  # 0 to 1
    time_lag_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analysis_date: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="correlations")  # noqa: F821

    __table_args__ = (Index("idx_correlations_analysis_date", "analysis_date"),)

    def __repr__(self) -> str:
        return f"<Correlation(id={self.id}, strength={self.correlation_strength})>"
