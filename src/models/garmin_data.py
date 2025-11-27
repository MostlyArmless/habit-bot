"""Garmin data model."""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.mixins import SoftDeleteMixin, TimestampMixin


class GarminMetricType(str, Enum):
    """Types of Garmin metrics we track."""

    SLEEP = "sleep"
    SLEEP_SCORE = "sleep_score"
    HRV = "hrv"
    RESTING_HR = "resting_hr"
    BODY_BATTERY = "body_battery"
    STRESS = "stress"
    STEPS = "steps"
    HEART_RATE = "heart_rate"  # All-day HR data
    ACTIVITIES = "activities"
    RESPIRATION = "respiration"
    SPO2 = "spo2"


class GarminData(Base, TimestampMixin, SoftDeleteMixin):
    """GarminData model for storing synced Garmin health data."""

    __tablename__ = "garmin_data"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # What type of metric this is
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # The calendar date this data corresponds to (e.g., "sleep for 2025-11-23")
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)

    # When the data was fetched from Garmin API
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Simple numeric value for metrics that have one (e.g., resting HR = 58)
    value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    # Full details from Garmin API response (JSON)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="garmin_data")  # noqa: F821

    __table_args__ = (
        # Only one record per user/metric_type/date
        UniqueConstraint("user_id", "metric_type", "metric_date", name="uq_garmin_user_metric_date"),
        Index("idx_garmin_data_metric_date", "metric_date"),
        Index("idx_garmin_data_metric_type", "metric_type"),
        Index("idx_garmin_data_user_date", "user_id", "metric_date"),
    )

    def __repr__(self) -> str:
        return f"<GarminData(id={self.id}, type='{self.metric_type}', date={self.metric_date})>"
