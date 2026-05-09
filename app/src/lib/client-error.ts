"use client";

import type { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";
import { ErrorCode } from "./error-codes";
import type { ActionResult } from "./errors";

/**
 * 统一处理 Server Action 的错误返回。
 *
 * 按 code 分发行为：
 * - UNAUTHORIZED：自动跳 /login 并带上 from，返回 { handled: true }
 * - FORBIDDEN / VERSION_CONFLICT：返回用户友好的 message，由调用方用 setError/toast 显示
 * - 其他：返回原始 message
 *
 * 使用方式：
 * ```ts
 * const result = await someAction(data);
 * const handled = handleActionResult(result, router);
 * if (!handled.ok && !handled.autoHandled) {
 *   setError(handled.message ?? "操作失败");
 * }
 * ```
 */
export type HandledResult<T> =
  | { ok: true; data: T }
  | { ok: false; autoHandled: true }
  | { ok: false; autoHandled: false; code: ErrorCode; message: string };

export function handleActionResult<T>(
  result: ActionResult<T>,
  router: AppRouterInstance,
  options?: { currentPath?: string },
): HandledResult<T> {
  if (result.success) {
    return { ok: true, data: result.data };
  }

  switch (result.code) {
    case ErrorCode.UNAUTHORIZED: {
      const from =
        options?.currentPath ?? (typeof window !== "undefined" ? window.location.pathname : "/");
      router.push(`/login?from=${encodeURIComponent(from)}`);
      return { ok: false, autoHandled: true };
    }
    default:
      return {
        ok: false,
        autoHandled: false,
        code: result.code,
        message: result.error,
      };
  }
}
