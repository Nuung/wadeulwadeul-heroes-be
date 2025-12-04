"""Main FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import classes, health, heroes, users
from app.core.auth import WadeulwadeulAuthMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication middleware (hackathon simple auth)
app.add_middleware(WadeulwadeulAuthMiddleware)

# Include routers - 모든 엔드포인트는 /api로 시작
app.include_router(health.router, prefix="/api")
app.include_router(heroes.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(classes.router, prefix="/api/v1")


@app.get("/api")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }
