"""One-day class model."""

from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.database import Base


class OneDayClass(Base):
    """원데이 클래스 모델."""

    __tablename__ = "classes"
    __table_args__: ClassVar[dict[str, str]] = (
        {"schema": "app"} if settings.environment == "production" else {}
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    creator_id: Mapped[UUID] = mapped_column(nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(nullable=False)
    capacity: Mapped[int] = mapped_column(nullable=False)
    years_of_experience: Mapped[str] = mapped_column(String(50), nullable=False)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    materials: Mapped[str] = mapped_column(Text, nullable=False)
    price_per_person: Mapped[str] = mapped_column(String(50), nullable=False)
    template: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    def __repr__(self) -> str:
        """String representation of OneDayClass."""
        return f"<OneDayClass(id={self.id}, category={self.category})>"
