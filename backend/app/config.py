from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        frozen=True,
        hide_input_in_errors=True,
    )

    database_url: PostgresDsn = Field(repr=False)
    database_pool_size: int = Field(default=5, ge=1)
    database_pool_timeout_seconds: int = Field(default=5, ge=1)
    database_statement_timeout_ms: int = Field(default=5000, ge=1)
