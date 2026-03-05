import httpx


class PyPIClient:
    """Stub — tests should fail (RED phase)."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch_package_info(self, package: str) -> dict:
        raise NotImplementedError
