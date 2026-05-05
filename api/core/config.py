from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://prism:prism@localhost:55432/prism"
    )
    redis_url: str = Field(default="redis://localhost:56379/0")
    app_env: str = Field(default="local")


settings = Settings()
