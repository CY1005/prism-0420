/**
 * Search service client — HTTP calls to FastAPI search endpoints.
 * Types mirror api/schemas/search.py exactly.
 */

const ANALYZER_BASE_URL = process.env.NEXT_PUBLIC_ANALYZER_URL || "http://localhost:8001";

export interface SearchResultItem {
  id: string;
  type: "node" | "dimension" | "issue";
  title: string;
  content_snippet: string;
  project_id: string | null;
  project_name: string | null;
  node_id: string | null;
  node_path: string | null;
  breadcrumb: string[] | null;
  dimension_type: string | null;
  issue_category: string | null;
  match_type?: "keyword" | "semantic" | "both";
  score?: number;
}

export interface SearchResponse {
  query: string;
  total: number;
  results: SearchResultItem[];
  search_mode?: "keyword" | "hybrid";
}

export type SearchResult = { ok: true; data: SearchResponse } | { ok: false; error: string };

export interface SearchOptions {
  projectId?: string;
  dimensionType?: string;
  issueCategory?: string;
  userId?: string;
  limit?: number;
}

export async function searchUnified(q: string, options?: SearchOptions): Promise<SearchResult> {
  try {
    const params = new URLSearchParams({ q });
    if (options?.projectId) params.set("project_id", options.projectId);
    if (options?.dimensionType) params.set("dimension_type", options.dimensionType);
    if (options?.issueCategory) params.set("issue_category", options.issueCategory);
    if (options?.userId) params.set("user_id", options.userId);
    if (options?.limit) params.set("limit", String(options.limit));

    const resp = await fetch(`${ANALYZER_BASE_URL}/search/unified?${params.toString()}`);
    if (!resp.ok) {
      const text = await resp.text();
      return { ok: false, error: `HTTP ${resp.status}: ${text}` };
    }
    const data = (await resp.json()) as SearchResponse;
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `搜索服务不可用: ${(e as Error).message}` };
  }
}
