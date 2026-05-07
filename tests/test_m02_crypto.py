"""M02 子片 3 — AES-256-GCM 横切 helper tests (api/auth/crypto.py)。"""

from __future__ import annotations

import base64
import os

import pytest

from api.auth.crypto import (
    CryptoDecryptError,
    CryptoKeyError,
    decrypt,
    encrypt,
    generate_key_b64,
)


def test_encrypt_decrypt_roundtrip():
    pt = "sk-ant-api-key-very-secret-1234567890"
    ct = encrypt(pt)
    assert ct != pt
    assert decrypt(ct) == pt


def test_encrypt_produces_different_ciphertext_each_call():
    """nonce 随机 → 同明文每次密文不同。"""
    pt = "same-plaintext"
    assert encrypt(pt) != encrypt(pt)


def test_decrypt_wrong_key_raises():
    """改 settings.encryption_key 后解旧 ciphertext → InvalidTag。"""
    from api.core.config import settings

    pt = "secret"
    ct = encrypt(pt)
    original = settings.encryption_key
    other = generate_key_b64()
    try:
        settings.encryption_key = other
        with pytest.raises(CryptoDecryptError):
            decrypt(ct)
    finally:
        settings.encryption_key = original


def test_decrypt_corrupted_ciphertext_raises():
    pt = "secret"
    ct = encrypt(pt)
    # flip last byte (broken auth tag)
    blob = bytearray(base64.b64decode(ct))
    blob[-1] ^= 0xFF
    bad = base64.b64encode(bytes(blob)).decode()
    with pytest.raises(CryptoDecryptError):
        decrypt(bad)


def test_decrypt_too_short_raises():
    short_b64 = base64.b64encode(b"x" * 5).decode()
    with pytest.raises(CryptoDecryptError):
        decrypt(short_b64)


def test_decrypt_invalid_base64_raises():
    with pytest.raises(CryptoDecryptError):
        decrypt("!!! not base64 !!!")


def test_decrypt_empty_raises():
    with pytest.raises(CryptoDecryptError):
        decrypt("")


def test_encrypt_none_raises():
    with pytest.raises(ValueError):
        encrypt(None)  # type: ignore[arg-type]


def test_missing_key_raises():
    from api.core.config import settings

    original = settings.encryption_key
    try:
        settings.encryption_key = ""
        with pytest.raises(CryptoKeyError):
            encrypt("x")
    finally:
        settings.encryption_key = original


def test_short_key_raises():
    from api.core.config import settings

    original = settings.encryption_key
    short = base64.b64encode(b"too-short").decode()
    try:
        settings.encryption_key = short
        with pytest.raises(CryptoKeyError):
            encrypt("x")
    finally:
        settings.encryption_key = original


def test_generate_key_b64_yields_32bytes():
    k = generate_key_b64()
    assert len(base64.b64decode(k)) == 32


def test_unicode_plaintext_roundtrip():
    pt = "中文密码 + emoji 🔑 + spaces"
    assert decrypt(encrypt(pt)) == pt


def test_long_plaintext_roundtrip():
    pt = "x" * 4000
    assert decrypt(encrypt(pt)) == pt


def test_nonce_freshness_uses_urandom(monkeypatch):
    """smoke: encrypt 调用 os.urandom(12) 取 nonce。"""
    calls = []
    real_urandom = os.urandom

    def spy(n):
        calls.append(n)
        return real_urandom(n)

    monkeypatch.setattr("api.auth.crypto.os.urandom", spy)
    encrypt("x")
    assert 12 in calls
