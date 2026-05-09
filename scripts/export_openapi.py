"""Export FastAPI OpenAPI schema to app/openapi.json (codegen 输入).

子片 1 driver. 不需 uvicorn 跑——直接调 app.openapi() 序列化。

Usage:
    uv run python scripts/export_openapi.py

Output: app/openapi.json (codegen 前重新生成 / 不入库)
"""

from __future__ import annotations

import json
from pathlib import Path

from api.main import app

OUTPUT = Path(__file__).resolve().parent.parent / "app" / "openapi.json"


def main() -> None:
    schema = app.openapi()
    OUTPUT.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
    paths_count = len(schema.get("paths", {}))
    schemas_count = len(schema.get("components", {}).get("schemas", {}))
    print(f"wrote {OUTPUT} — {paths_count} paths / {schemas_count} component schemas")


if __name__ == "__main__":
    main()
