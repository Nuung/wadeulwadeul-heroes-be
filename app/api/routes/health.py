"""Health check endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])


class PingResponse(BaseModel):
    """Ping response model."""

    status: str
    message: str


@router.get("/ping", response_model=PingResponse)
async def ping() -> PingResponse:
    """
    Ping endpoint for health checks.

    Returns:
        PingResponse: Simple ping response with status and message
    """
    return PingResponse(status="ok", message="pong")
