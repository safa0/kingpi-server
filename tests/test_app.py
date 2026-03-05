"""
App-level tests: verify the FastAPI application is correctly configured.

These tests check the application's structure and standard endpoints rather
than any specific feature. They answer: "Is the app wired up correctly?"

Three things are tested here:
1. Routes are registered under the expected prefix (/api/v1)
2. The health check endpoint works and returns the expected shape
3. FastAPI's auto-generated OpenAPI schema is accessible

The `client` fixture (from conftest.py) is used for HTTP tests.
`test_app_has_api_v1_routes` is synchronous — it inspects the app object
directly without making HTTP requests, so no async client is needed.
"""
from kingpi.app import create_app


def test_app_has_api_v1_routes():
    """The app should have at least one route under /api/v1.

    `create_app()` is a factory function (the Application Factory pattern)
    that constructs and returns a fresh FastAPI app each time. Using a factory
    rather than a module-level global makes the app easier to test (each test
    can get a clean instance) and avoids import-time side effects.

    `app.routes` is a list of route objects. We use `getattr(r, "path", "")`
    to safely get the path attribute — some internal FastAPI routes (like the
    exception handlers) may not have a `path` attribute.
    """
    app = create_app()
    route_paths = [getattr(r, "path", "") for r in app.routes]
    has_v1 = any("/api/v1" in path for path in route_paths)
    assert has_v1, f"No /api/v1 routes found. Routes: {route_paths}"


async def test_health_endpoint(client):
    # Health checks are used by load balancers and orchestrators (e.g., Kubernetes)
    # to determine if the service is alive and ready to receive traffic.
    # A simple {"status": "ok"} is the minimal contract — no auth required.
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_openapi_schema_available(client):
    # FastAPI auto-generates an OpenAPI 3.x JSON schema from your route
    # definitions and Pydantic models. This powers the Swagger UI at /docs.
    # Testing its availability confirms the app boots without schema errors.
    response = await client.get("/openapi.json")
    assert response.status_code == 200
