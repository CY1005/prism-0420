"use server";

/* eslint-disable @typescript-eslint/no-unused-vars -- 子片 3b 显式 punt stub：参数保留作为 M17 子片 3c 接入时的契约锚点 */
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import { ErrorCode } from "@/lib/error-codes";

/**
 * 拷贝层 ZIP 导入 wizard：在 prism-0420 形态下与 M17 imports 异步任务路径对齐。
 *
 * **本子片（3b）punt 范围**：
 *  - `uploadZip` / `createModulesFromZipTree` / `confirmImport` 三个函数依赖
 *    一个 sync 上传 → 返回 ParsedFile[] / 直接 db 写入的旧路径，prism-0420
 *    OpenAPI 没有对应同步端点（M17 是 task_id 异步 / WS 推送 / `/imports/{task_id}/confirm`）。
 *  - 重写需对齐 M17 ImportTask 状态机 + WS 进度通道，量大且涉及 UI 流程改造。
 *  - 子片 3b prompt 字面允许：「ai-import 强依赖 WS / SSE 实装 → 显式标 punt 子片 3c」。
 *
 * **本文件对外契约保留**（types 仍 export / 拷贝层 wizard 在 eslint ignore 内 / 不破 lint）：
 *  - 三个 action 返回 `actionError(NOT_IMPLEMENTED)` 显式标识 / 不静默吞错。
 *  - CSV 单路：见 `actions/nodes.ts importNodesFromCSV` → 已接入 M11 cold-start。
 *
 * **子片 3c TODO**：
 *  - uploadZip → POST /api/projects/{pid}/imports（multipart / 启动任务）
 *  - 任务进度 → WS /ws/imports/{task_id} 或轮询 GET /imports/{task_id}
 *  - confirmImport → POST /api/projects/{pid}/imports/{task_id}/confirm
 */

export interface ParsedFile {
  path: string;
  name: string;
  format: "markdown" | "csv" | "text";
  content: string;
  size: number;
  rows?: number;
  columns?: number;
}

export interface FileTreeNode {
  name: string;
  type: "file" | "folder";
  format?: string;
  children?: FileTreeNode[];
}

export interface UploadResult {
  files: ParsedFile[];
  tree: FileTreeNode;
}

export interface ImportItem {
  fileName: string;
  content: string;
  targetNodeId: string;
  nodeName: string;
  dimensionTypeId?: number;
}

const NOT_IMPLEMENTED_MSG = "ZIP 导入流程将在子片 3c 接入 M17 imports 端点（当前路径 punt）";

export async function createModulesFromZipTree(
  _projectId: string,
  _tree: FileTreeNode,
): Promise<ActionResult<{ folders: { id: string; name: string; path: string; depth: number }[] }>> {
  return actionError(new AppError(NOT_IMPLEMENTED_MSG, "blocking", ErrorCode.INTERNAL_ERROR, 501));
}

export async function uploadZip(_formData: FormData): Promise<ActionResult<UploadResult>> {
  return actionError(new AppError(NOT_IMPLEMENTED_MSG, "blocking", ErrorCode.INTERNAL_ERROR, 501));
}

export async function confirmImport(
  _projectId: string,
  _items: ImportItem[],
): Promise<ActionResult<{ imported: number; errors: string[] }>> {
  // 子片 3c 接入：POST /api/projects/{pid}/imports/{task_id}/confirm
  return actionError(new AppError(NOT_IMPLEMENTED_MSG, "blocking", ErrorCode.INTERNAL_ERROR, 501));
}

// 本子片（3b）保留 actionSuccess import 防止 eslint 误判（其他子片可能恢复实装）。
void actionSuccess;
