/**
 * Project stats service client.
 * Types mirror api/schemas/project.py exactly.
 */

const ANALYZER_BASE_URL = process.env.NEXT_PUBLIC_ANALYZER_URL || "http://localhost:8001";

export interface ProjectStats {
  project_id: string;
  project_name: string;
  total_folders: number;
  total_files: number;
  total_dimension_records: number;
  avg_completion_percent: number;
  dimension_type_count: number;
}

export interface TreeNodeOverview {
  id: string;
  name: string;
  type: "folder" | "file";
  depth: number;
  filled_dimensions: number;
  total_dimensions: number;
  completion_percent: number;
  children: TreeNodeOverview[];
}

export interface ProjectTreeOverview {
  project_id: string;
  project_name: string;
  tree: TreeNodeOverview[];
}

export type StatsResult<T> = { ok: true; data: T } | { ok: false; error: string };

export async function getProjectStats(projectId: string): Promise<StatsResult<ProjectStats>> {
  try {
    const resp = await fetch(`${ANALYZER_BASE_URL}/api/projects/${projectId}/stats`);
    if (!resp.ok) {
      return { ok: false, error: `HTTP ${resp.status}` };
    }
    const data = (await resp.json()) as ProjectStats;
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `服务不可用: ${(e as Error).message}` };
  }
}

export async function getProjectTreeOverview(
  projectId: string,
): Promise<StatsResult<ProjectTreeOverview>> {
  try {
    const resp = await fetch(`${ANALYZER_BASE_URL}/api/projects/${projectId}/tree-overview`);
    if (!resp.ok) {
      return { ok: false, error: `HTTP ${resp.status}` };
    }
    const data = (await resp.json()) as ProjectTreeOverview;
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `服务不可用: ${(e as Error).message}` };
  }
}
