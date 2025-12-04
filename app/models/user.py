"""User model for database."""

import enum
from datetime import UTC, datetime
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.database import Base


class UserType(str, enum.Enum):
    """User type enumeration."""

    YOUNG = "young"
    OLD = "old"


class User(Base):
    """
    User database model.

    Note: PostgreSQL uses 'app' schema, SQLite does not support schemas.
    Reference: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html
    """

    __tablename__ = "users"
    __table_args__: ClassVar[dict[str, str]] = (
        {"schema": "app"} if settings.environment == "production" else {}
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    type: Mapped[UserType] = mapped_column(
        Enum(UserType, native_enum=False, length=10),
        nullable=False,
        default=UserType.YOUNG,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(id={self.id}, name={self.name}, email={self.email}, type={self.type.value})>"
