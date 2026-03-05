"""
Database layer for KingPi.

This package encapsulates all database access — connection management,
session factories, and repository implementations. Keeping DB concerns
here means the rest of the application never imports SQLAlchemy directly,
making it easy to swap storage backends or add connection pooling later.

Typical contents as the project grows:
- `engine.py`  — async SQLAlchemy engine and session factory
- `models.py`  — ORM table models (mapped to DB tables)
- `repos/`     — repository classes that wrap queries behind clean interfaces
"""
