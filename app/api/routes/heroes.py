"""Heroes API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.hero import Hero

router = APIRouter(prefix="/heroes", tags=["heroes"])


class HeroCreate(BaseModel):
    """Hero creation schema."""

    name: str
    description: str | None = None
    level: int = 1


class HeroResponse(BaseModel):
    """Hero response schema."""

    id: UUID
    name: str
    description: str | None
    level: int

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[HeroResponse])
async def list_heroes(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[Hero]:
    """
    List all heroes with pagination.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of heroes
    """
    result = await db.execute(select(Hero).offset(skip).limit(limit))
    heroes = result.scalars().all()
    return list(heroes)


@router.get("/{hero_id}", response_model=HeroResponse)
async def get_hero(hero_id: UUID, db: AsyncSession = Depends(get_db)) -> Hero:
    """
    Get a specific hero by ID.

    Args:
        hero_id: UUID of the hero
        db: Database session

    Returns:
        Hero object

    Raises:
        HTTPException: If hero not found
    """
    result = await db.execute(select(Hero).where(Hero.id == hero_id))
    hero = result.scalar_one_or_none()

    if hero is None:
        raise HTTPException(status_code=404, detail="Hero not found")

    return hero


@router.post("/", response_model=HeroResponse, status_code=201)
async def create_hero(
    hero_data: HeroCreate, db: AsyncSession = Depends(get_db)
) -> Hero:
    """
    Create a new hero.

    Args:
        hero_data: Hero creation data
        db: Database session

    Returns:
        Created hero object
    """
    hero = Hero(**hero_data.model_dump())
    db.add(hero)
    await db.flush()
    await db.refresh(hero)
    return hero


@router.delete("/{hero_id}", status_code=204)
async def delete_hero(hero_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    """
    Delete a hero by ID.

    Args:
        hero_id: UUID of the hero
        db: Database session

    Raises:
        HTTPException: If hero not found
    """
    result = await db.execute(select(Hero).where(Hero.id == hero_id))
    hero = result.scalar_one_or_none()

    if hero is None:
        raise HTTPException(status_code=404, detail="Hero not found")

    await db.delete(hero)
