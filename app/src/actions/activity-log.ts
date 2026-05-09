"use server";

/* eslint-disable @typescript-eslint/no-unused-vars -- 子片 3c：logActivity / logActivityAuto 是 no-op 兼容层（参数保留作 M16 service 层 write_event 调用契约的锚点 / 子片 5 移除残留 caller 后删函数） */
import { redirect } from "next/navigation";
import { serverApiGet, UnauthenticatedError } from "@/lib/server-http-client";
import type { components } from "@/types/api";

type ActivityStreamResponse = components["schemas"]["ActivityStreamResponse"];
type ActivityLogItem = components["schemas"]["ActivityLogItem"];

async function withAuthRedirect<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    if (error instanceof UnauthenticatedError) {
      redirect("/login");
    }
    throw error;
  }
}

/**
 * 后端 activity_log 写由 service 层 write_event 触发（design §10）/ 前端不再客户端写。
 * 旧 logActivity / logActivityAuto 仅返回 void，实现替换为 no-op 以兼容残留 caller / 子片 5 移除调用点。
 */
export async function logActivity(_params: {
  projectId: string;
  userId: string;
  actionType: string;
  targetType: string;
  targetId: string;
  summary: string;
  metadata?: Record<string, unknown>;
}): Promise<void> {
  // no-op: prism-0420 activity_log 由 backend service 层写
}

export async function logActivityAuto(_params: {
  projectId: string;
  actionType: string;
  targetType: string;
  targetId: string;
  summary: string;
  metadata?: Record<string, unknown>;
}): Promise<void> {
  // no-op: 同上
}

export async function getActivityLogs(
  projectId: string,
  page: number = 1,
  pageSize: number = 20,
): Promise<{ logs: ActivityLogItem[]; page: number; pageSize: number; total: number }> {
  return withAuthRedirect(async () => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    const data = await serverApiGet<ActivityStreamResponse>(
      `/api/projects/${projectId}/activity-stream?${params}`,
    );
    return { logs: data.items, page: data.page, pageSize: data.page_size, total: data.total };
  });
}
