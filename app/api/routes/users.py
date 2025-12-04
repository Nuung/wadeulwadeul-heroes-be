"""Users API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User, UserType

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    """User creation schema."""

    name: str
    email: EmailStr | None = None
    type: UserType = UserType.YOUNG


class UserUpdate(BaseModel):
    """User update schema."""

    name: str | None = None
    email: EmailStr | None = None
    type: UserType | None = None


class UserResponse(BaseModel):
    """User response schema."""

    id: UUID
    name: str
    email: str | None
    type: UserType

    model_config = {"from_attributes": True}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current authenticated user information.

    Requires 'wadeulwadeul-user' header with user UUID.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user object

    Example:
        curl -H "wadeulwadeul-user: <user-uuid>" http://localhost:8000/api/v1/users/me
    """
    return current_user


@router.get("/", response_model=list[UserResponse])
async def list_users(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[User]:
    """
    List all users with pagination.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of users
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return list(users)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db)) -> User:
    """
    Get a specific user by ID.

    Args:
        user_id: UUID of the user
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If user not found
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate, db: AsyncSession = Depends(get_db)
) -> User:
    """
    Create a new user.

    Args:
        user_data: User creation data
        db: Database session

    Returns:
        Created user object

    Raises:
        HTTPException: If email already exists
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(**user_data.model_dump())
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID, user_data: UserUpdate, db: AsyncSession = Depends(get_db)
) -> User:
    """
    Update a user by ID.

    Args:
        user_id: UUID of the user
        user_data: User update data
        db: Database session

    Returns:
        Updated user object

    Raises:
        HTTPException: If user not found or email already exists
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if email already exists (if email is being updated)
    if user_data.email is not None and user_data.email != user.email:
        result = await db.execute(select(User).where(User.email == user_data.email))
        existing_user = result.scalar_one_or_none()

        if existing_user is not None:
            raise HTTPException(status_code=400, detail="Email already registered")

    # Update only provided fields
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    """
    Delete a user by ID.

    Args:
        user_id: UUID of the user
        db: Database session

    Raises:
        HTTPException: If user not found
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
