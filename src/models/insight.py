"""Insight model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ARRAY, Boolean, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Insight(Base):
    """Insight model for storing generated insights and recommendations."""

    __tablename__ = "insights"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    insight_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # correlation, anomaly, pattern, recommendation
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)  # 0 to 1
    actionable: Mapped[bool] = mapped_column(Boolean, default=True)
    categories: Mapped[list[str] | None] = mapped_column(ARRAY(String(100)), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="insights")  # noqa: F821

    __table_args__ = (
        Index("idx_insights_generated_at", "generated_at"),
        Index("idx_insights_insight_type", "insight_type"),
    )

    def __repr__(self) -> str:
        return f"<Insight(id={self.id}, title='{self.title}')>"
