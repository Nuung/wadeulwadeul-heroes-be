"""One-day class CRUD endpoints."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.class_ import OneDayClass
from app.models.user import User, UserType

router = APIRouter(prefix="/classes", tags=["classes"])


class ClassBase(BaseModel):
    """공통 필드."""

    category: str
    location: str
    start_time: datetime
    duration_minutes: int
    capacity: int
    notes: str | None = None

    @field_validator("start_time")
    @classmethod
    def normalize_start_time(cls, value: datetime) -> datetime:
        """tz-aware면 UTC로 변환 후 naive로 저장."""
        if value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value


class ClassCreate(ClassBase):
    """생성 요청 스키마."""

    pass


class ClassResponse(ClassBase):
    """응답 스키마."""

    id: UUID
    creator_id: UUID

    model_config = {"from_attributes": True}


@router.post("/", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
async def create_class(
    payload: ClassCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OneDayClass:
    """
    원데이 클래스 생성 (OLD 사용자만 허용).
    """
    if current_user.type != UserType.OLD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only OLD users can create classes",
        )

    new_class = OneDayClass(
        creator_id=current_user.id,
        category=payload.category,
        location=payload.location,
        start_time=payload.start_time,
        duration_minutes=payload.duration_minutes,
        capacity=payload.capacity,
        notes=payload.notes,
    )

    db.add(new_class)
    await db.flush()
    await db.refresh(new_class)
    return new_class


@router.get("/", response_model=list[ClassResponse])
async def list_classes(
    skip: int = 0,
    limit: int = 100,
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OneDayClass]:
    """
    원데이 클래스 목록 조회.
    """
    result = await db.execute(
        select(OneDayClass).offset(skip).limit(limit)
    )
    classes = result.scalars().all()
    return list(classes)


@router.get("/{class_id}", response_model=ClassResponse)
async def get_class_by_id(
    class_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OneDayClass:
    """
    원데이 클래스 단건 조회.
    """
    result = await db.execute(
        select(OneDayClass).where(OneDayClass.id == class_id)
    )
    one_day_class = result.scalar_one_or_none()

    if one_day_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    return one_day_class


class ClassUpdate(BaseModel):
    """수정 요청 스키마."""

    category: str | None = None
    location: str | None = None
    start_time: datetime | None = None
    duration_minutes: int | None = None
    capacity: int | None = None
    notes: str | None = None

    @field_validator("start_time")
    @classmethod
    def normalize_start_time(cls, value: datetime | None) -> datetime | None:
        """tz-aware면 UTC로 변환 후 naive로 저장."""
        if value is None:
            return value
        if value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value


@router.put("/{class_id}", response_model=ClassResponse)
async def update_class(
    class_id: UUID,
    payload: ClassUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OneDayClass:
    """
    원데이 클래스 수정 (작성자=OLD 사용자만).
    """
    result = await db.execute(select(OneDayClass).where(OneDayClass.id == class_id))
    one_day_class = result.scalar_one_or_none()

    if one_day_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    if current_user.type != UserType.OLD or one_day_class.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only creator OLD user can modify this class",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(one_day_class, field, value)

    await db.flush()
    await db.refresh(one_day_class)
    return one_day_class


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class(
    class_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    원데이 클래스 삭제 (작성자=OLD 사용자만).
    """
    result = await db.execute(select(OneDayClass).where(OneDayClass.id == class_id))
    one_day_class = result.scalar_one_or_none()

    if one_day_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    if current_user.type != UserType.OLD or one_day_class.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only creator OLD user can delete this class",
        )

    await db.delete(one_day_class)
    await db.flush()
