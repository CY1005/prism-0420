from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(default="postgresql+asyncpg://prism:prism@localhost:5432/prism")
    redis_url: str = Field(default="redis://localhost:6379/0")
    app_env: str = Field(default="local")

    jwt_secret: str = Field(default="dev-only-jwt-secret-change-me-in-prod-min-32-chars")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_ttl_seconds: int = Field(default=3600)

    internal_token: str = Field(default="dev-only-internal-token-change-me-in-prod-min-32-chars")
    internal_signature_window_seconds: int = Field(default=300)

    # M01
    refresh_token_ttl_days: int = Field(default=30)
    max_failed_logins: int = Field(default=5)
    account_lock_minutes: int = Field(default=15)

    bootstrap_admin_email: str | None = Field(default=None)
    bootstrap_admin_password: str | None = Field(default=None)
    bootstrap_admin_name: str = Field(default="Platform Admin")

    # M02 — AES-256-GCM 密钥 (base64 of 32 bytes); 默认 dev-only key (32B, b64 = 44 chars)
    # 生产部署必须覆盖；密钥轮转 / HSM 留 §8.0 必补清单
    encryption_key: str = Field(default="ZGV2LW9ubHktYWVzLTMyYnl0ZS1lbmNyeXB0aW9uLWs=")


settings = Settings()
