"use server";

import { serverApiPostDownload, type DownloadResponse } from "@/lib/server-http-client";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import type { components } from "@/types/api";

type MultiNodeExportRequest = components["schemas"]["MultiNodeExportRequest"];
type SingleNodeExportRequest = components["schemas"]["SingleNodeExportRequest"];
type ExportIncludeOptions = components["schemas"]["ExportIncludeOptions"];

/**
 * Sprint 1 Task 1.1（P22-3c-6 收口）：原 ExportPayload = unknown 让消费方裸用 .content/.filename
 * 真因是 client wrapper 不支持 text/binary 响应。改用 serverApiPostDownload 从 Content-Disposition
 * 提取 filename + body.text() 提取 content，类型化为 DownloadResponse 给消费方稳定使用。
 */
export type ExportPayload = DownloadResponse;

/**
 * 入口 A：多 node 导出 → POST /api/projects/{pid}/exports
 * 后端响应 text/markdown bytes + Content-Disposition: attachment; filename="..."
 * （design §7 + export_router._markdown_response）
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
    const data = await serverApiPostDownload(`/api/projects/${projectId}/exports`, body);
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
    const data = await serverApiPostDownload(
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
 * （ZIP 导出 / product_line scope 不在 design §7）。Phase 2.3 评估补充。
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
