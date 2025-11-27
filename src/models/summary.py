"""Summary model for storing pre-generated activity summaries."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from src.database import Base


class Summary(Base):
    """Model for storing pre-generated activity summaries.

    Summaries are generated periodically by background tasks and cached
    in the database to avoid blocking API requests.
    """

    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    period = Column(String(50), nullable=False)  # 'today', 'yesterday', 'week'
    period_label = Column(String(100), nullable=False)  # 'Today', 'Yesterday', 'Past 7 Days'
    summary_text = Column(Text, nullable=False)
    entry_count = Column(Integer, nullable=False, default=0)
    categories = Column(JSON, nullable=False, default=list)  # List of category strings

    # Timestamps
    period_start = Column(DateTime, nullable=False)  # Start of the period being summarized
    period_end = Column(DateTime, nullable=False)  # End of the period being summarized
    generated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    def __repr__(self) -> str:
        return f"<Summary(id={self.id}, user_id={self.user_id}, period={self.period}, generated_at={self.generated_at})>"
