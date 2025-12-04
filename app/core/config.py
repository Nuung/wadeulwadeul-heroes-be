"""Application configuration using pydantic-settings."""

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "Wadeulwadeul Heroes API"
    app_version: str = "0.1.0"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Environment (local or production)
    environment: str = "local"

    # Database settings (PostgreSQL - only used in production)
    db_host: str = ""
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres123"
    db_name: str = "wadeulwadeul_db"
    db_echo: bool = False

    # Database pool settings
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_pre_ping: bool = True

    @computed_field
    @property
    def database_url(self) -> str:
        """
        Build database URL based on environment.

        Returns:
            - SQLite (aiosqlite) for local development
            - PostgreSQL (asyncpg) for production

        Reference: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
        """
        env = self.environment.lower()

        # Use SQLite for local development
        if env == "local":
            return "sqlite+aiosqlite:///./wadeulwadeul_local.db"

        if not self.db_host:
            raise ValueError("DB_HOST is required when ENVIRONMENT is production")

        # Use PostgreSQL for production
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
