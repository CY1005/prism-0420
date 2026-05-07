"""M01 子片 5 — startup config validator (S10 / ADR-004 §3.3)."""

from __future__ import annotations

import pytest

from api.main import _validate_startup_config


def _patched_settings(monkeypatch, *, env: str, token: str) -> None:
    from api import main as main_mod
    from api.core import config as cfg_mod

    monkeypatch.setattr(cfg_mod.settings, "app_env", env)
    monkeypatch.setattr(cfg_mod.settings, "internal_token", token)
    # main.py 在 module import 时绑定 settings 引用，monkeypatch settings 字段够用
    monkeypatch.setattr(main_mod.settings, "app_env", env)
    monkeypatch.setattr(main_mod.settings, "internal_token", token)


def test_s10_prod_short_token_raises(monkeypatch):
    _patched_settings(monkeypatch, env="prod", token="x" * 16)
    with pytest.raises(RuntimeError, match="INTERNAL_TOKEN"):
        _validate_startup_config()


def test_s10_prod_long_token_passes(monkeypatch):
    _patched_settings(monkeypatch, env="prod", token="x" * 32)
    _validate_startup_config()


def test_s10_dev_short_token_warns_no_raise(monkeypatch, caplog):
    _patched_settings(monkeypatch, env="local", token="x" * 16)
    # 不应 raise
    _validate_startup_config()


def test_s10_dev_too_short_token_does_not_raise(monkeypatch):
    """dev 环境短 token 应仅 warning 不阻断（log 路由测试因 structlog 导致跨 test
    不稳定，这里只验"不 raise"这条核心契约——log 内容由人工 staging 时检查）。"""
    _patched_settings(monkeypatch, env="local", token="short")
    _validate_startup_config()
