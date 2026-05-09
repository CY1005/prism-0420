/**
 * 业务错误码（全局单一真相源）
 *
 * 所有业务错误必须使用此处定义的 code，禁止自由编造字符串。
 * 新增错误语义：先在此处加 code → 再在 errors.ts 加 Errors.XXX → 再使用。
 *
 * 前后端共用：前端按 code 分发 UX 行为，后端按 code 返回 AppError。
 */
export const ErrorCode = {
  // 认证 / 授权
  UNAUTHORIZED: "UNAUTHORIZED",
  FORBIDDEN: "FORBIDDEN",
  ACCOUNT_DISABLED: "ACCOUNT_DISABLED",
  ACCOUNT_LOCKED: "ACCOUNT_LOCKED",

  // 数据冲突
  VERSION_CONFLICT: "VERSION_CONFLICT",
  DUPLICATE_ENTRY: "DUPLICATE_ENTRY",

  // 业务校验
  VALIDATION_ERROR: "VALIDATION_ERROR",
  NOT_FOUND: "NOT_FOUND",

  // 外部服务
  AI_UNAVAILABLE: "AI_UNAVAILABLE",
  AI_TIMEOUT: "AI_TIMEOUT",
  NETWORK_ERROR: "NETWORK_ERROR",

  // 系统 / 配置
  CONFIG_MISSING: "CONFIG_MISSING",
  INTERNAL_ERROR: "INTERNAL_ERROR",

  // 操作结果（info）
  SAVE_SUCCESS: "SAVE_SUCCESS",
} as const;

export type ErrorCode = (typeof ErrorCode)[keyof typeof ErrorCode];
