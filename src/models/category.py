"""Category model."""

from datetime import datetime

from sqlalchemy import ARRAY, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class Category(Base):
    """Category model for tracking different health categories."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequency_per_day: Mapped[int] = mapped_column(Integer, default=4)
    preferred_times: Mapped[list[str] | None] = mapped_column(ARRAY(Time), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"
