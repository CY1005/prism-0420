"use server";

/* eslint-disable @typescript-eslint/no-unused-vars -- 子片 3b 显式 punt stub：参数保留作为 M17 子片 3c 接入时的契约锚点 */
import { type ActionResult, actionError, AppError } from "@/lib/errors";
import { ErrorCode } from "@/lib/error-codes";

/**
 * 拷贝层 AI 智能导入 wizard（M17 imports 后端形态）。
 *
 * **本子片（3b）DOWNGRADE 范围**：
 *  - 旧路径调老 Prism web 内置 `/api/import/ai-*` 端点（默认 `localhost:8001`）。
 *  - prism-0420 OpenAPI 真实路径：`/api/projects/{pid}/imports*`（task_id 异步 / WS 进度通道）。
 *  - 端点 shape 完全不同（task_id 流转 + ImportTaskStatusEnum 11 态 + WS 推送）。
 *  - 子片 3b prompt 字面允许：「ai-import 强依赖 WS / SSE 实装 → 显式标 punt 子片 3c」。
 *
 * **本文件契约保留**（types 仍 export / consumer ai-import-wizard.tsx 在 eslint ignore 内）：
 *  - 4 个 action 返回 `actionError(NOT_IMPLEMENTED)` / 不静默吞错。
 *  - drizzle / requireAuth / `localhost:8001` 老路径全删除（拷贝层债务关闸）。
 *
 * **子片 3c TODO**（接入 M17）：
 *  - aiAnalyzeZip → POST /api/projects/{pid}/imports（multipart）→ task_id
 *  - 进度 → GET /api/projects/{pid}/imports/{task_id} 轮询，或 WS /ws/imports/{task_id}
 *  - aiConfirmImport → POST /api/projects/{pid}/imports/{task_id}/confirm
 *  - aiUndoImport → POST /api/projects/{pid}/imports/{task_id}/cancel + DELETE 已建节点
 *  - aiAdjustMapping → POST /api/projects/{pid}/imports/{task_id}/review
 */

export interface MappingRow {
  id: string;
  index: number;
  title: string;
  source_path: string;
  content: string;
  extracted_content: string;
  recommended_module_id: string;
  recommended_module_name: string;
  recommended_dimension_id: number | null;
  recommended_dimension_key: string;
  recommended_dimension_name: string;
  confidence: number;
  reason: string;
  product_line_tags: string[];
  conflict: boolean;
  conflict_message: string | null;
  existing_node_id: string | null;
  selected: boolean;
  action: "import" | "skip" | "merge";
}

export interface RelationHint {
  from_index: number;
  to_index: number;
  from_title: string;
  to_title: string;
  reason: string;
}

export interface AvailableModule {
  id: string;
  name: string;
  path: string;
  depth: number;
}

export interface AvailableDimension {
  id: number;
  key: string;
  name: string;
}

export interface AIAnalyzeResult {
  session_id: string;
  mapping_rows: MappingRow[];
  relations: RelationHint[];
  available_modules: AvailableModule[];
  available_dimensions: AvailableDimension[];
  stats: {
    total_files: number;
    total_items: number;
    high_confidence: number;
    medium_confidence: number;
    low_confidence: number;
    conflicts: number;
    relation_hints: number;
  };
}

export interface AIConfirmResult {
  session_id: string;
  imported: number;
  merged: number;
  skipped: number;
  errors: string[];
  created_node_ids: string[];
  relations_created: number;
}

export interface MappingAdjustment {
  id: string;
  recommended_module_id: string;
  recommended_dimension_id: number | null;
}

const PUNT_MSG =
  "AI 智能导入将在子片 3c 接入 M17 ImportTask 异步任务 + WS 进度通道（当前路径 punt）";

export async function aiAnalyzeZip(
  _projectId: string,
  _files: object[],
): Promise<ActionResult<AIAnalyzeResult>> {
  return actionError(new AppError(PUNT_MSG, "blocking", ErrorCode.INTERNAL_ERROR, 501));
}

export async function aiAdjustMapping(
  _projectId: string,
  _sessionId: string,
  _adjustments: MappingAdjustment[],
): Promise<void> {
  // fire-and-forget / 子片 3c 接入 M17 review 端点
}

export async function aiConfirmImport(
  _projectId: string,
  _sessionId: string,
  _mappingRows: MappingRow[],
): Promise<ActionResult<AIConfirmResult>> {
  return actionError(new AppError(PUNT_MSG, "blocking", ErrorCode.INTERNAL_ERROR, 501));
}

export async function aiUndoImport(
  _projectId: string,
  _sessionId: string,
  _createdNodeIds: string[],
): Promise<ActionResult<{ deleted: number; errors: string[] }>> {
  return actionError(new AppError(PUNT_MSG, "blocking", ErrorCode.INTERNAL_ERROR, 501));
}
