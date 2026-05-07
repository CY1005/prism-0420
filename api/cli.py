"""M01 CLI: ``python -m api.cli create-admin --email a@b.c --password ... --name N``."""

from __future__ import annotations

import argparse
import asyncio
import sys

from api.core.db import SessionLocal
from api.errors.exceptions import EmailAlreadyExistsError, PasswordTooWeakError
from api.services.auth_service import get_auth_service


async def _create_admin(email: str, password: str, name: str) -> int:
    svc = get_auth_service()
    async with SessionLocal() as db:
        try:
            await svc.create_admin(db, email=email, password=password, name=name)
        except PasswordTooWeakError:
            print("Password too weak (min 8 characters)", file=sys.stderr)
            return 1
        except EmailAlreadyExistsError:
            print("Email already exists", file=sys.stderr)
            return 1
    print(f"Created admin: {email}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="api.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-admin")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--name", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "create-admin":
        return asyncio.run(_create_admin(args.email, args.password, args.name))
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
