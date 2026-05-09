import { redirect } from "next/navigation";
import { UnauthenticatedError } from "@/lib/server-http-client";

/**
 * Server-side 读 helper：UnauthenticatedError 直接 redirect /login（spec 06 §3 字面）。
 * 其他错误透出给 caller 决定（toast / error.tsx）。
 *
 * Phase 2.3 子 sprint C — P22-3b-1 关闭：原 11 处 inline 实现合并到此 horizontal helper。
 */
export async function withAuthRedirect<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    if (error instanceof UnauthenticatedError) {
      redirect("/login");
    }
    throw error;
  }
}
