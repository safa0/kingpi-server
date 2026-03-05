from pypi_server.app import create_app


def test_app_has_api_v1_routes():
    """The app should have at least one route under /api/v1."""
    app = create_app()
    route_paths = [getattr(r, "path", "") for r in app.routes]
    has_v1 = any("/api/v1" in path for path in route_paths)
    assert has_v1, f"No /api/v1 routes found. Routes: {route_paths}"


async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_openapi_schema_available(client):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
