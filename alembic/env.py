"""Alembic environment configuration for async SQLAlchemy."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import your app's config and models
from app.core.config import settings
from app.core.database import Base

# Import all models for autogenerate support
from app.models import Hero, User  # noqa: F401

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url from settings
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = Base.metadata


def include_object(_object, _name, _type_, _reflected, _compare_to):  # noqa: ARG001
    """
    Filter objects for autogenerate.

    Reference: https://alembic.sqlalchemy.org/en/latest/autogenerate.html
    """
    # Include all objects
    return True


def process_revision_directives(_context, _revision, directives):
    """
    Post-process migration directives to add schema for PostgreSQL.

    This ensures migrations work correctly in both SQLite (no schema)
    and PostgreSQL (with 'app' schema).

    Reference: https://alembic.sqlalchemy.org/en/latest/cookbook.html
    """
    # Only add schema if we're in production (PostgreSQL)
    if settings.environment != "production":
        return

    # Add schema to all table operations
    for directive in directives:
        if hasattr(directive, 'upgrade_ops'):
            for ops in directive.upgrade_ops.ops:
                if hasattr(ops, 'schema'):
                    ops.schema = 'app'
                # Handle batch operations
                if hasattr(ops, 'ops'):
                    for op in ops.ops:
                        if hasattr(op, 'schema'):
                            op.schema = 'app'


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    version_table_schema = "app" if settings.environment == "production" else None
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        process_revision_directives=process_revision_directives,
        version_table_schema=version_table_schema,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    version_table_schema = "app" if settings.environment == "production" else None
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        process_revision_directives=process_revision_directives,
        version_table_schema=version_table_schema,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
