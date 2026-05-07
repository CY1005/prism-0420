#!/usr/bin/env bash
# CI lint 守护：本地 + pre-commit + GitHub Actions 共用入口。
#
# 当前规约：
#   R13-1: api/errors/codes.py 中每个业务 ErrorCode 必有 api/errors/exceptions.py
#          中对应 AppError 子类（INTERNAL_ERROR 除外——由 unhandled-exception
#          fallback 复用，无独立子类）。
#
# 后续可继续追加 R5-X / R10-X 等守护项。
set -euo pipefail

cd "$(dirname "$0")/.."

CODES_FILE="api/errors/codes.py"
EXC_FILE="api/errors/exceptions.py"

# ErrorCode 业务码（不含 INTERNAL_ERROR）：匹配 ^    UPPER_NAME = "lower_value" 形式
# （N1 命名规范：enum 名 UPPER_SNAKE，value 全小写 snake；详见 design/00-architecture/08-namespaces.md）
ERROR_CODES=$(grep -cE '^[[:space:]]+[A-Z][A-Z_]+ = "[a-z_]+"$' "$CODES_FILE")
INTERNAL_COUNT=$(grep -cE '^[[:space:]]+INTERNAL_ERROR = "internal_error"$' "$CODES_FILE")
BUSINESS_CODES=$((ERROR_CODES - INTERNAL_COUNT))

# AppError 子类：任何 *Error 类，继承自 AppError 或其 *Error 子类（中间继承允许，
# design §9 / §13 例：OldPasswordMismatchError(ValidationError)、
# UserNotFoundError(NotFoundError)）。基类 AppError 不计。
APP_ERRORS=$(grep -cE '^class [A-Z][A-Za-z]*Error\([A-Z][A-Za-z]*Error\):' "$EXC_FILE")

if [ "$BUSINESS_CODES" -ne "$APP_ERRORS" ]; then
  echo "ERROR (R13-1): 业务 ErrorCode 数 ($BUSINESS_CODES, INTERNAL_ERROR 除外)" \
       "与 AppError 子类数 ($APP_ERRORS) 不一致。"
  echo "  $CODES_FILE 中 ErrorCode 业务码:"
  grep -E '^[[:space:]]+[A-Z][A-Z_]+ = "[a-z_]+"$' "$CODES_FILE" \
    | grep -v INTERNAL_ERROR
  echo "  $EXC_FILE 中 AppError 子类:"
  grep -E '^class [A-Z][A-Za-z]*Error\([A-Z][A-Za-z]*Error\):' "$EXC_FILE"
  exit 1
fi

echo "✓ R13-1: $BUSINESS_CODES 业务 ErrorCode = $APP_ERRORS AppError 子类"
