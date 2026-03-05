from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./kingpi.db"
    api_prefix: str = "/api/v1"
    debug: bool = False
    pypi_request_timeout_seconds: float = 10.0

    model_config = {"env_prefix": "KINGPI_"}
