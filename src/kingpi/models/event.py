"""
SQLAlchemy ORM model for package event counters.

DESIGN: Aggregate table, not raw events
-----------------------------------------
We store ONE row per (package, event_type) pair with a running counter and
the most recent timestamp. This is an intentional tradeoff:

  Pros:
  - Reads are O(1) — no GROUP BY or COUNT(*) over millions of rows
  - Writes are atomic via INSERT ... ON CONFLICT DO UPDATE (upsert)
  - Row-level locking means concurrent writers don't block each other

  Cons:
  - We lose individual event history (can't query "all installs last Tuesday")
  - If we need raw event logs later, we'd add a second append-only table

For this project's requirements (total count + last timestamp), the aggregate
approach is the right fit.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from kingpi.db.engine import Base


class PackageEvent(Base):
    """One row per (package, event_type) — stores count + last timestamp.

    The composite unique constraint on (package, event_type) is what makes
    the upsert (INSERT ... ON CONFLICT) work: PostgreSQL uses it to detect
    conflicts and route to the DO UPDATE branch instead of raising an error.
    """

    __tablename__ = "package_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    package: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # timezone=True stores timestamps as TIMESTAMPTZ in PostgreSQL, ensuring
    # timezone info is preserved. Without this, UTC timestamps could be
    # silently reinterpreted in the server's local timezone.
    last_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("package", "event_type", name="uq_package_event_type"),
    )
