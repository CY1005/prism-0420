"use server";

import { requireAuth } from "@/lib/auth";
import { checkProjectAccess } from "@/services/permission.service";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import { ErrorCode } from "@/lib/error-codes";
import type {
  LayerResult,
  GenerateTestPointsRequest,
  AITestPoint,
  GenerateTestPointsResponse,
  ComparisonGenerateRequest,
  ComparisonGenerateResponse,
  BackfillRequest,
  BackfillResponse,
  AnalyzerResult,
} from "@/services/analyzer";

const API_BASE = process.env.API_URL ?? "http://localhost:8001";

export interface AffectedNodesResult {
  node_id: string;
  affected_node_ids: string[];
  analysis_record_id: string | null;
}

export async function getAffectedNodes(
  nodeId: string,
  projectId: string,
): Promise<ActionResult<AffectedNodesResult>> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "viewer");

    const params = new URLSearchParams({ node_id: nodeId, project_id: projectId });
    const res = await fetch(`${API_BASE}/api/analyze/affected-nodes?${params.toString()}`);

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: "查询影响节点失败" }));
      return actionError(
        new AppError(
          body.detail || "查询影响节点失败",
          "blocking",
          ErrorCode.INTERNAL_ERROR,
          res.status,
        ),
      );
    }

    const data: AffectedNodesResult = await res.json();
    return actionSuccess(data);
  } catch (error) {
    return actionError(error);
  }
}

// ─── Helper for internal POST ─────────────────────

async function internalPost<T>(path: string, body: unknown): Promise<AnalyzerResult<T>> {
  try {
    const resp = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      const text = await resp.text();
      return { ok: false, error: `HTTP ${resp.status}: ${text}` };
    }
    const data = (await resp.json()) as T;
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `分析服务不可用: ${(e as Error).message}` };
  }
}

// ─── Analysis Server Actions ─────────────────────

export async function saveAnalysisAction(
  projectId: string,
  nodeId: string,
  layers: LayerResult[],
): Promise<AnalyzerResult<{ dimension_record_id: string; message: string }>> {
  const analysisResult = JSON.stringify(
    layers.map((l) => ({
      level: l.level,
      affected_modules: l.affected_modules,
      completeness_issues: l.completeness_issues,
      suggestions: l.suggestions,
    })),
  );
  const lastMeta = layers.findLast((l) => l.metadata)?.metadata;
  return internalPost("/api/analyze/save", {
    project_id: projectId,
    node_id: nodeId,
    analysis_result: analysisResult,
    metadata: lastMeta
      ? {
          model: lastMeta.model,
          tokens_used: lastMeta.tokens_used,
          analysis_time_ms: lastMeta.analysis_time_ms,
        }
      : null,
  });
}

export async function generateTestPointsAIAction(
  req: GenerateTestPointsRequest,
): Promise<AnalyzerResult<GenerateTestPointsResponse>> {
  return internalPost<GenerateTestPointsResponse>("/api/analyze/generate-test-points", req);
}

export async function saveTestPointsAction(
  projectId: string,
  nodeId: string,
  testPoints: AITestPoint[],
): Promise<
  AnalyzerResult<{ saved_count: number; dimension_record_ids: string[]; message: string }>
> {
  return internalPost("/api/analyze/save-test-points", {
    project_id: projectId,
    node_id: nodeId,
    test_points: testPoints.map((tp) => ({
      title: tp.title,
      description: tp.description,
      priority: tp.priority,
      category: tp.category,
      steps: tp.steps,
      expected_result: tp.expected_result,
    })),
  });
}

// ─── Comparison Server Actions ───────────────────

export async function generateComparisonAction(
  req: ComparisonGenerateRequest,
): Promise<AnalyzerResult<ComparisonGenerateResponse>> {
  return internalPost<ComparisonGenerateResponse>("/api/comparison/generate", req);
}

export async function backfillRowAction(
  req: BackfillRequest,
): Promise<AnalyzerResult<BackfillResponse>> {
  return internalPost<BackfillResponse>(`/api/comparison/${req.comparison_id}/backfill`, {
    row_index: req.row_index,
    node_id: req.node_id,
    competitor_id: req.competitor_id,
  });
}

export async function exportComparisonAction(
  comparisonId: string,
): Promise<AnalyzerResult<string>> {
  try {
    const resp = await fetch(
      `${API_BASE}/api/comparison/${encodeURIComponent(comparisonId)}/export`,
    );
    if (!resp.ok) {
      const text = await resp.text();
      return { ok: false, error: `HTTP ${resp.status}: ${text}` };
    }
    const data = (await resp.json()) as { markdown: string };
    return { ok: true, data: data.markdown };
  } catch (e) {
    return { ok: false, error: `分析服务不可用: ${(e as Error).message}` };
  }
}
