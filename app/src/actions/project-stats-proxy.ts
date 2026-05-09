"use server";

import { redirect } from "next/navigation";
import { serverApiGet, UnauthenticatedError } from "@/lib/server-http-client";
import type { components } from "@/types/api";

type OverviewResponse = components["schemas"]["OverviewResponse"];
type OverviewStats = components["schemas"]["OverviewStats"];
type NodeOverview = components["schemas"]["NodeOverview"];

export type ProjectStats = OverviewStats & { project_id: string };
export type TreeNodeOverview = NodeOverview;
export type StatsResult<T> = { ok: true; data: T } | { ok: false; error: string };

/**
 * 子片 3c — 旧实装走 port 8001 + INTERNAL_TOKEN 微服务（prism-0420 OpenAPI 不存在该路径）。
 * 重写走 /api/projects/{pid}/overview（actions/panorama.ts.getProjectStats 已实装同源 endpoint）。
 * 函数签名保留以兼容 overview/page.tsx 残留 import（在 eslint ignore / 子片 5 cleanup 替换为 panorama）。
 */
async function fetchOverview(projectId: string): Promise<OverviewResponse> {
  try {
    return await serverApiGet<OverviewResponse>(`/api/projects/${projectId}/overview`);
  } catch (error) {
    if (error instanceof UnauthenticatedError) {
      redirect("/login");
    }
    throw error;
  }
}

export async function getProjectStatsAction(projectId: string): Promise<StatsResult<ProjectStats>> {
  try {
    const overview = await fetchOverview(projectId);
    return { ok: true, data: { ...overview.stats, project_id: overview.project_id } };
  } catch (e) {
    return { ok: false, error: `服务不可用: ${(e as Error).message}` };
  }
}

export async function getProjectTreeOverviewAction(
  projectId: string,
): Promise<StatsResult<{ tree: TreeNodeOverview[] }>> {
  try {
    const overview = await fetchOverview(projectId);
    return { ok: true, data: { tree: overview.tree } };
  } catch (e) {
    return { ok: false, error: `服务不可用: ${(e as Error).message}` };
  }
}
