"use server";

import { requireAuth } from "@/lib/auth";
import type { ProjectStats, TreeNodeOverview } from "@/services/project-stats";

const API_BASE = process.env.API_URL ?? "http://localhost:8001";
const INTERNAL_TOKEN = process.env.INTERNAL_TOKEN ?? "";

type StatsResult<T> = { ok: true; data: T } | { ok: false; error: string };

export async function getProjectStatsAction(projectId: string): Promise<StatsResult<ProjectStats>> {
  try {
    const user = await requireAuth();
    const resp = await fetch(`${API_BASE}/api/projects/${projectId}/stats`, {
      headers: {
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-User-Id": user.id,
      },
    });
    if (!resp.ok) return { ok: false, error: `HTTP ${resp.status}` };
    const data = (await resp.json()) as ProjectStats;
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `服务不可用: ${(e as Error).message}` };
  }
}

export async function getProjectTreeOverviewAction(
  projectId: string,
): Promise<StatsResult<{ tree: TreeNodeOverview[] }>> {
  try {
    const user = await requireAuth();
    const resp = await fetch(`${API_BASE}/api/projects/${projectId}/tree-overview`, {
      headers: {
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-User-Id": user.id,
      },
    });
    if (!resp.ok) return { ok: false, error: `HTTP ${resp.status}` };
    const data = (await resp.json()) as { tree: TreeNodeOverview[] };
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `服务不可用: ${(e as Error).message}` };
  }
}
