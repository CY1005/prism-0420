"use server";

import { withAuthRedirect } from "@/lib/server-action-helpers";
import { serverApiGet } from "@/lib/server-http-client";
import { type ActionResult, actionError, actionSuccess } from "@/lib/errors";
import type { components } from "@/types/api";

type OverviewResponse = components["schemas"]["OverviewResponse"];
type OverviewStats = components["schemas"]["OverviewStats"];
type NodeOverview = components["schemas"]["NodeOverview"];

export type ProjectStats = OverviewStats & { project_id: string };
export type TreeNodeOverview = NodeOverview;

/**
 * Sprint 1 Task 1.2 (P22-3c-2 收口) — 旧 StatsResult<T> {ok,data} 双 result 类型并行
 * 已统一为 ActionResult<T> {success,data}（@/lib/errors 范式 / 跟 actions/panorama.ts 等
 * mainstream actions 一致 / overview/page.tsx caller 同步改 r.ok→r.success）。
 *
 * 子片 3c — 旧实装走 port 8001 + INTERNAL_TOKEN 微服务（prism-0420 OpenAPI 不存在该路径）。
 * 重写走 /api/projects/{pid}/overview（actions/panorama.ts.getProjectStats 已实装同源 endpoint）。
 * 函数签名保留以兼容 overview/page.tsx 残留 import / Phase 2.3 后续替换为 panorama.getProjectStats。
 */
export async function getProjectStatsAction(
  projectId: string,
): Promise<ActionResult<ProjectStats>> {
  try {
    return await withAuthRedirect(async () => {
      const overview = await serverApiGet<OverviewResponse>(`/api/projects/${projectId}/overview`);
      return actionSuccess({ ...overview.stats, project_id: overview.project_id });
    });
  } catch (error) {
    return actionError(error);
  }
}

export async function getProjectTreeOverviewAction(
  projectId: string,
): Promise<ActionResult<{ tree: TreeNodeOverview[] }>> {
  try {
    return await withAuthRedirect(async () => {
      const overview = await serverApiGet<OverviewResponse>(`/api/projects/${projectId}/overview`);
      return actionSuccess({ tree: overview.tree });
    });
  } catch (error) {
    return actionError(error);
  }
}
