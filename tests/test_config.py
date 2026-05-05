from api.core.config import Settings


def test_settings_defaults_are_local_friendly():
    s = Settings(_env_file=None)
    assert "asyncpg" in s.database_url
    assert s.redis_url.startswith("redis://")
    assert s.app_env == "local"
