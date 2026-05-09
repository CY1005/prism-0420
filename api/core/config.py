from pydantic import Field, model_validator
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

    # Phase 2.2 子片 2 — 前端 CORS + refresh cookie（spec 06 §2 / B 路径）
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Phase 2.3 子 sprint A — 05-security §8.6 punt #1 关闭
    @model_validator(mode="after")
    def _prod_cors_guard(self) -> "Settings":
        if self.app_env == "prod":
            for origin in self.cors_origins:
                low = origin.lower()
                if "localhost" in low or "127.0.0.1" in low:
                    raise ValueError(
                        f"app_env=prod 禁止 cors_origins 含 localhost/127.0.0.1（当前：{origin}）"
                    )
                if not low.startswith("https://"):
                    raise ValueError(
                        f"app_env=prod 要求 cors_origins 走 https://（当前：{origin}）"
                    )
        return self


settings = Settings()
