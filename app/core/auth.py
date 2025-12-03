"""Authentication middleware and dependencies for hackathon project."""

from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import AsyncSessionLocal
from app.models.user import User

# Header key for user identification
AUTH_HEADER_KEY = "wadeulwadeul-user"


class WadeulwadeulAuthMiddleware(BaseHTTPMiddleware):
    """
    Simple authentication middleware for hackathon.

    Reads 'wadeulwadeul-user' header value (user email) and loads the user.
    Stores the user in request.state.user for downstream access.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Process the request and load user from header."""
        user_email = request.headers.get(AUTH_HEADER_KEY)

        # Initialize user as None
        request.state.user = None

        if user_email:
            # Create a new database session for this middleware
            async with AsyncSessionLocal() as session:
                try:
                    result = await session.execute(
                        select(User).where(User.email == user_email)
                    )
                    user = result.scalar_one_or_none()

                    if user:
                        # Store user in request state
                        request.state.user = user
                except Exception:
                    # If any error occurs, just leave user as None
                    pass

        response = await call_next(request)
        return response


async def get_current_user(request: Request) -> User:
    """
    Dependency to get the current authenticated user.

    Raises 401 if no user is found in request.state.
    Use this for protected endpoints that require authentication.

    Args:
        request: FastAPI request object

    Returns:
        User object

    Raises:
        HTTPException: 401 if user not authenticated

    Example:
        @router.get("/me")
        async def get_me(user: User = Depends(get_current_user)):
            return user
    """
    user = getattr(request.state, "user", None)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication required. Please provide '{AUTH_HEADER_KEY}' header with user email.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(request: Request) -> User | None:
    """
    Dependency to get the current user (optional).

    Returns None if no user is found in request.state.
    Use this for endpoints where authentication is optional.

    Args:
        request: FastAPI request object

    Returns:
        User object or None

    Example:
        @router.get("/items")
        async def list_items(user: User | None = Depends(get_current_user_optional)):
            if user:
                # Return personalized items
                pass
            else:
                # Return public items
                pass
    """
    return getattr(request.state, "user", None)
