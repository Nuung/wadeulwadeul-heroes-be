"""Hero model for database."""

from datetime import UTC, datetime
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.database import Base


class Hero(Base):
    """
    Hero database model.

    Note: PostgreSQL uses 'app' schema, SQLite does not support schemas.
    Reference: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html
    """

    __tablename__ = "heroes"
    __table_args__: ClassVar[dict[str, str]] = (
        {"schema": "app"} if settings.environment == "production" else {}
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[int] = mapped_column(default=1, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    def __repr__(self) -> str:
        """String representation of Hero."""
        return f"<Hero(id={self.id}, name={self.name}, level={self.level})>"
