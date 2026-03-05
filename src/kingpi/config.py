from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./kingpi.db"
    api_prefix: str = "/api/v1"
    debug: bool = False

    model_config = {"env_prefix": "KINGPI_"}
