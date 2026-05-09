/**
 * Comparison service client.
 * Types mirror api/schemas/comparison.py.
 */

const ANALYZER_BASE_URL = process.env.NEXT_PUBLIC_ANALYZER_URL || "http://localhost:8001";

export interface CompetitorRef {
  node_id: string;
  node_name: string;
  node_path: string;
  content: Record<string, unknown>;
}

export interface ComparisonResponse {
  project_id: string;
  dimension_key: string;
  items: CompetitorRef[];
  total: number;
}

export type ComparisonResult =
  | { ok: true; data: ComparisonResponse }
  | { ok: false; error: string };

export async function getComparison(
  projectId: string,
  dimensionKey: string = "competitor_ref",
): Promise<ComparisonResult> {
  try {
    const params = new URLSearchParams({ dimension_key: dimensionKey });
    const resp = await fetch(`${ANALYZER_BASE_URL}/api/projects/${projectId}/comparison?${params}`);
    if (!resp.ok) return { ok: false, error: `HTTP ${resp.status}` };
    const data = (await resp.json()) as ComparisonResponse;
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `服务不可用: ${(e as Error).message}` };
  }
}
