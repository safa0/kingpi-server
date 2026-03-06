"""
Alembic migration environment — configured for async PostgreSQL.

WHY async migrations?
---------------------
Our app uses asyncpg (async PostgreSQL driver). Alembic's default env.py
uses synchronous connections, which won't work with an async driver.
The `run_async_migrations()` pattern below uses SQLAlchemy's
`async_engine.connect()` to run migrations through the async driver.

HOW autogenerate works:
-----------------------
Alembic compares our `target_metadata` (from Base.metadata, which knows
about all ORM models) against the actual database schema, and generates
migration scripts for the diff. This only works if all models are imported
before this point — hence the `import kingpi.models.event` below.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import our Base so Alembic can see all registered ORM models.
# Every model that inherits from Base automatically registers its table
# in Base.metadata — Alembic reads this to generate migration diffs.
from kingpi.db.engine import Base
import kingpi.models.event  # noqa: F401 — registers PackageEvent with Base.metadata

config = context.config

# Override the ini-file URL with the env var if set — keeps credentials
# out of source control. The ini placeholder is only used as a fallback
# for local development without Docker.
import os

db_url = os.environ.get("KINGPI_DATABASE_URL") or config.get_main_option("sqlalchemy.url")
config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL scripts without connecting to the database."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine — required for asyncpg driver."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
