"""
Async SQLAlchemy engine and session factory.

WHY async?
----------
FastAPI is an async framework — blocking the event loop with synchronous DB
calls would stall all concurrent requests. SQLAlchemy 2.0's async extension
(`sqlalchemy.ext.asyncio`) lets us `await` database operations, keeping the
event loop free to handle other requests while waiting for I/O.

WHY a factory function?
-----------------------
`create_async_engine` and `async_sessionmaker` are created once at startup
and reused across the app's lifetime. Wrapping this in a module keeps the
engine config in one place and lets us swap connection strings easily
(e.g., test DB vs production DB).
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models.

    SQLAlchemy's DeclarativeBase provides the `metadata` object that tracks
    all table definitions. Alembic reads this metadata to auto-generate
    migration scripts — so every model must inherit from this Base.
    """


def build_engine(
    database_url: str, *, echo: bool = False
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create an async engine and session factory from a database URL.

    Returns a tuple of (engine, session_factory) so the caller can manage
    the engine lifecycle (dispose on shutdown) and use the session factory
    to create per-request sessions.

    Args:
        echo: When True, logs all SQL statements (useful for debugging,
              should be False in production to avoid leaking query data).
    """
    engine = create_async_engine(database_url, echo=echo)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory
