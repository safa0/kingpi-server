"""
Domain models for KingPi.

WHY a separate models layer?
-----------------------------
Domain models represent the core business concepts (Package, Event, etc.)
independent of any framework. Unlike Pydantic schemas (in `schemas/`), which
define the API contract, domain models capture the internal representation
used by services and the database layer.

This separation follows the "Clean Architecture" principle: business logic
depends on domain models, not on HTTP request/response shapes. As the app
grows, domain dataclasses or SQLAlchemy ORM models will live here.
"""
