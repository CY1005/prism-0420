"""一次性解锁 e2e@example.com（清 locked_until + failed_login_count / dogfooding 调试用）"""

from __future__ import annotations

import asyncio
import sys


async def main() -> int:
    from sqlalchemy import select

    from api.core.db import SessionLocal
    from api.models.user import User

    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "e2e@example.com"))
        user = result.scalar_one_or_none()
        if user is None:
            print("[unlock] user not found")
            return 1
        user.locked_until = None
        user.failed_login_count = 0
        await db.commit()
        print("[unlock] cleared locked_until + failed_login_count")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
