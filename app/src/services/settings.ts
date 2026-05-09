/**
 * Project settings service client.
 * Types mirror api/schemas/settings.py.
 */

const ANALYZER_BASE_URL = process.env.NEXT_PUBLIC_ANALYZER_URL || "http://localhost:8001";

export interface ProjectSettings {
  project_id: string;
  name: string;
  description: string | null;
  template_type: string;
  members: Array<{ user_id: string; role: string }>;
  dimension_configs: Array<{
    id: number;
    dimension_key: string;
    dimension_name: string;
    enabled: boolean;
    sort_order: number;
  }>;
}

export type SettingsResult<T> = { ok: true; data: T } | { ok: false; error: string };

export async function getProjectSettings(
  projectId: string,
): Promise<SettingsResult<ProjectSettings>> {
  try {
    const resp = await fetch(`${ANALYZER_BASE_URL}/api/projects/${projectId}/settings`);
    if (!resp.ok) return { ok: false, error: `HTTP ${resp.status}` };
    const data = (await resp.json()) as ProjectSettings;
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `服务不可用: ${(e as Error).message}` };
  }
}

export async function updateProjectSettings(
  projectId: string,
  update: { name?: string; description?: string },
): Promise<SettingsResult<{ status: string }>> {
  try {
    const resp = await fetch(`${ANALYZER_BASE_URL}/api/projects/${projectId}/settings`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(update),
    });
    if (!resp.ok) return { ok: false, error: `HTTP ${resp.status}` };
    const data = await resp.json();
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `服务不可用: ${(e as Error).message}` };
  }
}
