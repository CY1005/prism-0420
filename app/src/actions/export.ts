"use server";

/* eslint-disable @typescript-eslint/no-unused-vars -- 子片 3c：exportProject NOT_IMPLEMENTED stub（prism-0420 OpenAPI 暂无项目级 ZIP 导出 / Phase 2.3 评估补充） */
import { serverApiPost } from "@/lib/server-http-client";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import type { components } from "@/types/api";

type MultiNodeExportRequest = components["schemas"]["MultiNodeExportRequest"];
type SingleNodeExportRequest = components["schemas"]["SingleNodeExportRequest"];
type ExportIncludeOptions = components["schemas"]["ExportIncludeOptions"];

export type ExportPayload = unknown;

/**
 * 入口 A：多 node 导出 → POST /api/projects/{pid}/exports
 * 后端 200 响应 schema 为 unknown（design §7 / R1-A 字段裁剪到 service / API 类型不强约束）。
 * 调用方按需解析（旧 { filename, content } 字段不再保证 / 子片 5 cleanup 对齐消费方）。
 */
export async function exportNodes(
  projectId: string,
  nodeIds: string[],
  include?: ExportIncludeOptions,
): Promise<ActionResult<ExportPayload>> {
  try {
    if (!nodeIds.length) {
      return actionError(new AppError("请选择要导出的节点", "blocking", "VALIDATION_ERROR"));
    }
    const body: MultiNodeExportRequest = { node_ids: nodeIds, ...(include && { include }) };
    const data = await serverApiPost<ExportPayload>(`/api/projects/${projectId}/exports`, body);
    logger.action("export.nodes", "self", { projectId, nodeCount: nodeIds.length });
    return actionSuccess(data);
  } catch (error) {
    return actionError(error);
  }
}

/**
 * 入口 B：单 node 导出 → POST /api/projects/{pid}/nodes/{nid}/export
 * 等价 A 传 node_ids=[node_id]（design §7）。
 */
export async function exportSingleNode(
  projectId: string,
  nodeId: string,
  include?: ExportIncludeOptions,
): Promise<ActionResult<ExportPayload>> {
  try {
    const body: SingleNodeExportRequest = include ? { include } : {};
    const data = await serverApiPost<ExportPayload>(
      `/api/projects/${projectId}/nodes/${nodeId}/export`,
      body,
    );
    logger.action("export.singleNode", "self", { projectId, nodeId });
    return actionSuccess(data);
  } catch (error) {
    return actionError(error);
  }
}

/**
 * 旧 exportProject(productLineId) 在 prism-0420 OpenAPI 无对应 endpoint
 * （ZIP 导出 / product_line scope 不在 design §7）。子片 5 后 Phase 2.3 评估补充。
 */
export async function exportProject(
  _projectId: string,
  _productLineId?: string,
): Promise<ActionResult<{ filename: string; content: string }>> {
  return actionError(
    new AppError(
      "项目级 ZIP 导出在 prism-0420 OpenAPI 暂未提供（Phase 2.3 评估补充）",
      "blocking",
      "INTERNAL_ERROR",
      501,
    ),
  );
}
