"""Class enrollment model."""

from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.database import Base


class Enrollment(Base):
    """원데이 클래스 신청."""

    __tablename__ = "enrollments"
    __table_args__: ClassVar[dict[str, str]] = (
        {"schema": "app"} if settings.environment == "production" else {}
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    class_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    applied_date: Mapped[str] = mapped_column(String(50), nullable=False)
    headcount: Mapped[int] = mapped_column(nullable=False)

    def __repr__(self) -> str:
        """String representation of Enrollment."""
        return f"<Enrollment(id={self.id}, class_id={self.class_id}, user_id={self.user_id})>"
