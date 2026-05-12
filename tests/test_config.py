from api.core.config import Settings


def test_settings_defaults_are_local_friendly(monkeypatch):
    # 验代码默认值；必须清环境变量，否则 CI 设的 APP_ENV/DATABASE_URL/REDIS_URL 会盖过代码 default
    for var in ("APP_ENV", "DATABASE_URL", "REDIS_URL"):
        monkeypatch.delenv(var, raising=False)
    s = Settings(_env_file=None)
    assert "asyncpg" in s.database_url
    assert s.redis_url.startswith("redis://")
    assert s.app_env == "local"
