from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./pypi_server.db"
    api_prefix: str = "/api/v1"
    debug: bool = False

    model_config = {"env_prefix": "PYPI_SERVER_"}
