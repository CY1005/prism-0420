"use server";

/* eslint-disable @typescript-eslint/no-unused-vars -- 子片 3b 部分 punt：SSE/test-points/comparison 6 个 stub 参数保留作为子片 3c 接 M13/M14 真端点的契约锚点 */
import { redirect } from "next/navigation";
import { serverApiGet, UnauthenticatedError } from "@/lib/server-http-client";
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

type AffectedNodesResponse = components["schemas"]["AffectedNodesResponse"];

/**
 * 拷贝层 analyze 路径迁移：
 *  - `getAffectedNodes` → 已 rebase 到 prism-0420 OpenAPI
 *      `GET /api/projects/{pid}/nodes/{nid}/analyze/affected-nodes`（M13 / R-X1）。
 *  - SSE/test-points/comparison/backfill 流程：旧实装走 Prism 内置 analyzer 微服务（localhost:8001）;
 *    prism-0420 OpenAPI 仅暴露 requirement/save/affected-nodes 三端点 + 单独 `/comparison/*` 路径，
 *    SSE 渲染契约 + test-points 实装路径 + comparison/backfill batch 路径需子片 3c 接 M13/M14 真实端点。
 *  - 子片 3b prompt 字面允许：「analysis SSE / 流式契约 → 显式标 punt 子片 3c 或 Phase 2.3」。
 */

async function withAuthRedirect<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    if (error instanceof UnauthenticatedError) {
      redirect("/login");
    }
    throw error;
  }
}

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
