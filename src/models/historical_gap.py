"""Historical gap model."""

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import TSRANGE
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class HistoricalGap(Base):
    """HistoricalGap model for tracking gaps in historical data."""

    __tablename__ = "historical_gaps"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    time_period: Mapped[str | None] = mapped_column(TSRANGE, nullable=True)
    gap_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # missing_data, incomplete_data, anomaly
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1-10
    follow_up_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="historical_gaps")  # noqa: F821

    __table_args__ = (
        Index("idx_historical_gaps_category", "category"),
        Index("idx_historical_gaps_priority", "priority"),
    )

    def __repr__(self) -> str:
        return f"<HistoricalGap(id={self.id}, category='{self.category}')>"
