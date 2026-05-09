"use server";

import { serverApiGet } from "@/lib/server-http-client";
import type { components } from "@/types/api";
import { withAuthRedirect } from "@/lib/server-action-helpers";

type ActivityStreamResponse = components["schemas"]["ActivityStreamResponse"];
type ActivityLogItem = components["schemas"]["ActivityLogItem"];

/**
 * 后端 activity_log 写由 service 层 write_event 触发（design §10）/ 前端不再客户端写。
 * 旧 logActivity / logActivityAuto no-op 兼容层 已删（Phase 2.3 子 sprint C / P22-3c-7 关闭）。
 */
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
    return {
      logs: data.items,
      page: data.page,
      pageSize: data.page_size,
      total: data.total ?? 0,
    };
  });
}
