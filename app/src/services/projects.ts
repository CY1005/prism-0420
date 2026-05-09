/**
 * Projects service client.
 * Types mirror api/schemas/project_list.py.
 */

const ANALYZER_BASE_URL = process.env.NEXT_PUBLIC_ANALYZER_URL || "http://localhost:8001";

export interface ProjectSummary {
  id: string;
  name: string;
  description: string | null;
  template_type: string;
  total_nodes: number;
  total_files: number;
  avg_completion: number;
  created_at: string | null;
}

export interface ProjectListResponse {
  projects: ProjectSummary[];
  total: number;
}

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string };

export async function listProjects(): Promise<ApiResult<ProjectListResponse>> {
  try {
    const resp = await fetch(`${ANALYZER_BASE_URL}/api/projects/`);
    if (!resp.ok) return { ok: false, error: `HTTP ${resp.status}` };
    const data = (await resp.json()) as ProjectListResponse;
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `服务不可用: ${(e as Error).message}` };
  }
}

export async function createProject(
  name: string,
  description?: string,
  templateType?: string,
): Promise<ApiResult<{ id: string; name: string }>> {
  try {
    const resp = await fetch(`${ANALYZER_BASE_URL}/api/projects/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        description: description || null,
        template_type: templateType || "custom",
      }),
    });
    if (!resp.ok) {
      const text = await resp.text();
      return { ok: false, error: `HTTP ${resp.status}: ${text}` };
    }
    const data = await resp.json();
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `服务不可用: ${(e as Error).message}` };
  }
}
