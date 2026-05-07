"""bcrypt password hashing 横切 helper（horizontal）。

# horizontal: 是
# owner: M01（design/02-modules/M01-user-account/00-design.md §6）
# 位置: api/auth/（横切层，对齐原则 6 + R-X6 + 04-layer Q7）
# 范畴: 密码学基础（bcrypt 单向 hash 凭据存储）

测试环境通过 ``BCRYPT_ROUNDS_OVERRIDE`` 把 cost 从默认 12 降到 4，加速测试。
"""

import os

import bcrypt


def _rounds() -> int:
    override = os.environ.get("BCRYPT_ROUNDS_OVERRIDE")
    if override:
        try:
            value = int(override)
            if 4 <= value <= 16:
                return value
        except ValueError:
            pass
    return 12


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=_rounds())
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
