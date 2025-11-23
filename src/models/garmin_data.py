"""Garmin data model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class GarminData(Base):
    """GarminData model for storing synced Garmin health data."""

    __tablename__ = "garmin_data"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    data_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # sleep, stress, steps, hrv, etc.
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="garmin_data")  # noqa: F821

    __table_args__ = (
        Index("idx_garmin_data_timestamp", "timestamp"),
        Index("idx_garmin_data_data_type", "data_type"),
    )

    def __repr__(self) -> str:
        return f"<GarminData(id={self.id}, data_type='{self.data_type}')>"
