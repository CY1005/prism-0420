import { ErrorCode } from "./error-codes";

/**
 * Next.js `redirect()` 抛 `Error` 含 `digest = "NEXT_REDIRECT;..."`，必须透出不能 catch 后吞。
 * 公共 API 未导出 isRedirectError（v15）/ 此处按 digest 字面识别。
 */
function isNextRedirectError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  const digest = (error as Error & { digest?: unknown }).digest;
  return typeof digest === "string" && digest.startsWith("NEXT_REDIRECT");
}

// 错误严重程度
export type ErrorSeverity = "blocking" | "warning" | "info";

// 应用错误类
export class AppError extends Error {
  constructor(
    message: string,
    public severity: ErrorSeverity,
    public code: ErrorCode,
    public statusCode: number = 400,
  ) {
    super(message);
    this.name = "AppError";
  }
}

// 预定义错误
export const Errors = {
  // 认证 (blocking)
  UNAUTHORIZED: new AppError("请先登录", "blocking", ErrorCode.UNAUTHORIZED, 401),
  FORBIDDEN: new AppError("无权限执行此操作", "blocking", ErrorCode.FORBIDDEN, 403),
  ACCOUNT_DISABLED: new AppError(
    "账号已被禁用，请联系管理员",
    "blocking",
    ErrorCode.ACCOUNT_DISABLED,
    403,
  ),
  ACCOUNT_LOCKED: new AppError("账号已锁定，请稍后重试", "blocking", ErrorCode.ACCOUNT_LOCKED, 423),

  // 数据冲突 (blocking)
  VERSION_CONFLICT: new AppError(
    "内容已被他人修改，请刷新后重试",
    "blocking",
    ErrorCode.VERSION_CONFLICT,
    409,
  ),
  DUPLICATE_ENTRY: new AppError("数据已存在", "blocking", ErrorCode.DUPLICATE_ENTRY, 409),

  // 业务校验 (blocking)
  VALIDATION_ERROR: (msg: string) => new AppError(msg, "blocking", ErrorCode.VALIDATION_ERROR, 400),
  NOT_FOUND: (resource: string) =>
    new AppError(`${resource}不存在`, "blocking", ErrorCode.NOT_FOUND, 404),

  // 外部服务 (warning)
  AI_SERVICE_UNAVAILABLE: new AppError(
    "AI分析服务暂时不可用，请稍后重试",
    "warning",
    ErrorCode.AI_UNAVAILABLE,
    503,
  ),
  AI_TIMEOUT: new AppError("AI分析超时，请稍后重试", "warning", ErrorCode.AI_TIMEOUT, 504),
  NETWORK_ERROR: new AppError("网络连接失败，请检查网络", "warning", ErrorCode.NETWORK_ERROR, 503),

  // 操作结果 (info) — 用于成功提示等
  SAVE_SUCCESS: new AppError("保存成功", "info", ErrorCode.SAVE_SUCCESS, 200),
};

// Server Action 统一返回类型
export type ActionResult<T = void> =
  | { success: true; data: T }
  | { success: false; error: string; code: ErrorCode; severity: ErrorSeverity };

// 包装 Server Action 的错误处理
// spec 06 §3：UnauthenticatedError → redirect("/login") 通过 NEXT_REDIRECT 抛出 / 必须透出不能吞。
export function actionError(error: unknown): ActionResult<never> {
  if (isNextRedirectError(error)) {
    throw error;
  }
  if (error instanceof AppError) {
    return { success: false, error: error.message, code: error.code, severity: error.severity };
  }
  // fallback：保留诊断信息到服务端日志（不回传前端以避免泄露细节）
  console.error("Unexpected error:", error);
  return {
    success: false,
    error: "操作失败，请重试",
    code: ErrorCode.INTERNAL_ERROR,
    severity: "warning",
  };
}

export function actionSuccess<T>(data: T): ActionResult<T> {
  return { success: true, data };
}
