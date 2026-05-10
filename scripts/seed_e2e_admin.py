"""Sprint 2 Task 2.1 — 一次性创 e2e admin user / 幂等。

为什么不走 BOOTSTRAP_ADMIN env：
- 现有 server 已 in-flight，加 env 需要重启
- 本脚本独立跑 / 不依赖 server / 直接走 SQLAlchemy + auth_service 创建路径
- 幂等：已存在则 skip / 退出 0

使用：
    uv run python scripts/seed_e2e_admin.py

然后 e2e fixtures 用 e2e@test.local / Password123! 登录拿 access_token。
"""

from __future__ import annotations

import asyncio
import sys

E2E_EMAIL = "e2e@example.com"
E2E_PASSWORD = "Password123!"
E2E_NAME = "E2E Test Admin"


async def main() -> int:
    from sqlalchemy import select

    from api.auth.password import hash_password
    from api.core.db import SessionLocal
    from api.models.user import User

    async with SessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == E2E_EMAIL))
        if existing.scalar_one_or_none() is not None:
            print(f"[seed_e2e_admin] {E2E_EMAIL} 已存在 / skip")
            return 0

        user = User(
            email=E2E_EMAIL,
            password_hash=hash_password(E2E_PASSWORD),
            name=E2E_NAME,
            role="platform_admin",
            status="active",
        )
        db.add(user)
        await db.commit()
        print(f"[seed_e2e_admin] 创建 {E2E_EMAIL} / role=platform_admin / status=active")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
