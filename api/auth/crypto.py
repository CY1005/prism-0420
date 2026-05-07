"""AES-256-GCM 加解密横切 helper（horizontal）。

# horizontal: 是
# owner: M02 (early adopter §7.1 B' 部分提前) — 多模块复用候选 (M13 读 ai_api_key prompt context / M16/M17 cron secret)
# 位置: api/auth/（横切层，对齐原则 6 + R-X6 + 04-layer Q7）
# 范畴: 05-security-baseline §4 数据加密 helper

设计来源：design/02-modules/M02-project/00-design.md §3.Z early adopter +
design/01-engineering/05-security-baseline.md §7.1 B' (部分提前) + §4 数据加密。

密钥从 settings.encryption_key 读（env ENCRYPTION_KEY，32 bytes base64）。
轮转 / HSM / 多密钥 fallback 留 §8.0 必补清单。
"""

from __future__ import annotations

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from api.core.config import settings

_NONCE_LEN = 12  # AES-GCM 标准 96-bit


class CryptoKeyError(ValueError):
    """密钥无效（缺失 / 长度错 / 非 base64）。"""


class CryptoDecryptError(ValueError):
    """解密失败（密文损坏 / 错密钥 / 错 nonce）。"""


def _key_bytes() -> bytes:
    raw = settings.encryption_key
    if not raw:
        raise CryptoKeyError("ENCRYPTION_KEY not configured")
    try:
        key = base64.b64decode(raw)
    except Exception as e:
        raise CryptoKeyError(f"ENCRYPTION_KEY not valid base64: {e}") from e
    if len(key) != 32:
        raise CryptoKeyError(f"ENCRYPTION_KEY decoded length {len(key)} != 32 bytes (AES-256)")
    return key


def encrypt(plaintext: str) -> str:
    """AES-256-GCM 加密 + base64 编码。返回 base64(nonce || ciphertext+tag)。"""
    if plaintext is None:
        raise ValueError("plaintext must not be None")
    key = _key_bytes()
    aes = AESGCM(key)
    nonce = os.urandom(_NONCE_LEN)
    ct = aes.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt(ciphertext_b64: str) -> str:
    """解密 base64(nonce || ciphertext+tag) 返回原文 str。"""
    if not ciphertext_b64:
        raise CryptoDecryptError("empty ciphertext")
    try:
        blob = base64.b64decode(ciphertext_b64)
    except Exception as e:
        raise CryptoDecryptError(f"ciphertext not valid base64: {e}") from e
    if len(blob) < _NONCE_LEN + 16:
        raise CryptoDecryptError("ciphertext too short")
    nonce, ct = blob[:_NONCE_LEN], blob[_NONCE_LEN:]
    key = _key_bytes()
    aes = AESGCM(key)
    try:
        pt = aes.decrypt(nonce, ct, associated_data=None)
    except InvalidTag as e:
        raise CryptoDecryptError("InvalidTag — wrong key or corrupted ciphertext") from e
    return pt.decode("utf-8")


def generate_key_b64() -> str:
    """工具函数：生成新的 32-byte AES-256 密钥（base64 编码字符串）。"""
    return base64.b64encode(os.urandom(32)).decode("ascii")
