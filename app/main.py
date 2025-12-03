"""Main FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, heroes, users
from app.core.auth import WadeulwadeulAuthMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    docs_url=settings.docs_url if settings.enable_docs else None,
    redoc_url=settings.redoc_url if settings.enable_docs else None,
    openapi_url=settings.openapi_url if settings.enable_docs else None,
    root_path=settings.root_path,
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

# Include routers
app.include_router(health.router)
app.include_router(heroes.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }
