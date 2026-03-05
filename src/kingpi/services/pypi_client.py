import httpx


class PackageNotFoundError(Exception):
    def __init__(self, package: str) -> None:
        self.package = package
        super().__init__(f"Package '{package}' not found on PyPI")


class PyPIUpstreamError(Exception):
    def __init__(self, package: str, status_code: int) -> None:
        self.package = package
        self.status_code = status_code
        super().__init__(f"PyPI returned {status_code} for package '{package}'")


class PyPIClient:
    """Stub — tests should fail (RED phase)."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch_package_info(self, package: str) -> dict:
        raise NotImplementedError
