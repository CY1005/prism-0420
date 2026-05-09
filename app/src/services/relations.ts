/**
 * Relations graph service client.
 * Types mirror api/schemas/relations.py.
 * Data format designed for React Flow consumption.
 */

const ANALYZER_BASE_URL = process.env.NEXT_PUBLIC_ANALYZER_URL || "http://localhost:8001";

export interface GraphNode {
  id: string;
  name: string;
  type: "folder" | "file";
  depth: number;
  completion_percent: number;
}

export interface GraphEdge {
  id: number;
  source: string;
  target: string;
  relation_type: "depends_on" | "related_to" | "conflicts_with";
  description: string | null;
}

export interface RelationGraphResponse {
  project_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export type GraphResult = { ok: true; data: RelationGraphResponse } | { ok: false; error: string };

export async function getRelationGraph(projectId: string): Promise<GraphResult> {
  try {
    const resp = await fetch(`${ANALYZER_BASE_URL}/api/projects/${projectId}/relations`);
    if (!resp.ok) return { ok: false, error: `HTTP ${resp.status}` };
    const data = (await resp.json()) as RelationGraphResponse;
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `服务不可用: ${(e as Error).message}` };
  }
}
