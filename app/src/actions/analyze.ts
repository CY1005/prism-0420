"use server";

import { serverApiGet } from "@/lib/server-http-client";
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
import type { components } from "@/types/api";
import { withAuthRedirect } from "@/lib/server-action-helpers";

type AffectedNodesResponse = components["schemas"]["AffectedNodesResponse"];

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
    return await withAuthRedirect(async () => {
      const data = await serverApiGet<AffectedNodesResponse>(
        `/api/projects/${projectId}/nodes/${nodeId}/analyze/affected-nodes`,
      );
      return actionSuccess({
        node_id: data.node_id,
        affected_node_ids: data.affected_node_ids,
        analysis_record_id: data.analysis_record_id ?? null,
      });
    });
  } catch (error) {
    return actionError(error);
  }
}

const PUNT_MSG_SSE =
  "需求 SSE 分析 / test-points / comparison batch 将在子片 3c 接入 M13/M14 真实端点（当前 punt）";

function puntResult<T>(): AnalyzerResult<T> {
  return { ok: false, error: PUNT_MSG_SSE };
}

export async function saveAnalysisAction(
  _projectId: string,
  _nodeId: string,
  _layers: LayerResult[],
): Promise<AnalyzerResult<{ dimension_record_id: string; message: string }>> {
  // 子片 3c 接入：POST /api/projects/{pid}/nodes/{nid}/analyze/save
  return puntResult();
}

export async function generateTestPointsAIAction(
  _req: GenerateTestPointsRequest,
): Promise<AnalyzerResult<GenerateTestPointsResponse>> {
  return puntResult();
}

export async function saveTestPointsAction(
  _projectId: string,
  _nodeId: string,
  _testPoints: AITestPoint[],
): Promise<
  AnalyzerResult<{ saved_count: number; dimension_record_ids: string[]; message: string }>
> {
  return puntResult();
}

export async function generateComparisonAction(
  _req: ComparisonGenerateRequest,
): Promise<AnalyzerResult<ComparisonGenerateResponse>> {
  return puntResult();
}

export async function backfillRowAction(
  _req: BackfillRequest,
): Promise<AnalyzerResult<BackfillResponse>> {
  return puntResult();
}

export async function exportComparisonAction(
  _comparisonId: string,
): Promise<AnalyzerResult<string>> {
  return puntResult();
}

// 防 unused-import 误判
void AppError;
void ErrorCode;
