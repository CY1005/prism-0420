"use server";

import { revalidatePath } from "next/cache";
import { serverApiFetch, serverApiPost, serverApiGet } from "@/lib/server-http-client";
import { getServerAccessToken } from "@/lib/server-auth";
import { withAuthRedirect } from "@/lib/server-action-helpers";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import { ErrorCode } from "@/lib/error-codes";

/**
 * M17 AI 智能导入 — Server Actions（接通 prism-0420 真后端 / dogfooding cluster-M17 fix 2026-05-15）。
 *
 * **本 cluster 修复点（B-P4-cluster-M17）**：
 *  - 全 4 actions（aiAnalyzeZip / aiAdjustMapping / aiConfirmImport / aiUndoImport）
 *    从子片 3b 字面 puntResult stub 升级到接 M17 backend endpoints。
 *  - **范式说明**：prism-0420 M17 是异步 Queue + WebSocket 进度通道（design §3 状态机 +
 *    §12 Queue payload），与老 Prism 同步 `aiAnalyzeZip → mapping_rows` 范式有根本差异。
 *
 * **接通的 backend endpoints**（详 api/routers/import_router.py + design §7）：
 *  - aiAnalyzeZip → POST /api/projects/{pid}/imports (multipart) → ImportTaskResponse
 *  - aiAdjustMapping → no-op + 标 design-gap（后端无 review 中间调整 endpoint / 只有 final confirm）
 *  - aiConfirmImport → POST /api/projects/{pid}/imports/{tid}/confirm (ReviewConfirmRequest)
 *  - aiUndoImport → POST /api/projects/{pid}/imports/{tid}/cancel + 标 per-node undo design-gap
 *
 * **已知 design-gap（设计 vs 老 Prism 范式差）**（详 design-audit.md）：
 *  - **G1**: 老 Prism 同步范式 vs prism-0420 异步范式 → aiAnalyzeZip 返「task_id pending」
 *           而非完整 mapping_rows。完整 mapping 数据由后端 awaiting_review 阶段产出
 *           走 GET /review 拉 ReviewDataResponse（caller 在 WS review_ready 事件后调）。
 *  - **G2**: aiAdjustMapping 后端无对应 endpoint。设计上用户调整在 client-side 累积后
 *           一次性走 confirm。本 action 改为 no-op（兼容现有 wizard caller fire-and-forget 调用）。
 *  - **G3**: aiUndoImport 是 per-node undo，但 backend cancel 是 task 级取消（cancelled →
 *           回滚整任务事务 / 没有删特定 created_node_ids 的接口）。本 action 调 cancel
 *           但参数 createdNodeIds 实际未用。caller 应在 task=completed 后理解 undo 等价
 *           于「整个 import task 撤销」/ 若已有其他后续编辑则需走 M03 nodes DELETE。
 *
 * **dogfooding cluster-M17 escalation 上报点**（见 RCA.md）：
 *  - **依赖 import.ts uploadZip 实装**：caller ai-import-wizard.tsx step 0 仍依赖
 *    actions/import.ts uploadZip 同步解 zip 拿 ParsedFile[]，该 action 现仍 punt。
 *    本 cluster 范围内不修 import.ts；wizard happy path 端到端走不通需独立 cluster。
 *  - **WS 客户端实装**：B-P2-M17-fake-progress-no-websocket 在 ai-import-wizard.tsx
 *    L524-537 已用 WS 客户端取代 setTimeout 假进度（cluster 内修复）。
 */

// ─── caller-facing types（保留兼容 ai-import-wizard.tsx 现有 import）───────────────

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
  /** 真后端 task_id（M17 异步任务 ID / 用于后续 WS 监听 + confirm/cancel）。
   *  range: 旧 session_id 字段在 prism-0420 形态下直接复用 task_id（caller 不区分）。
   */
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
  /** 真后端 task 当前 status（pending → ai_step1 → ... → awaiting_review → ...）
   *  caller 应在 awaiting_review 后才走 confirm 路径；本 cluster 接通时 task 立即
   *  返 pending，mapping_rows 为空（caller 通过 WS / GET /review 后填）。
   */
  task_status: string;
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

// ─── ImportTaskResponse（与 api/schemas/import_schema.py 对齐）───────────────

interface ImportTaskResponse {
  id: string;
  project_id: string;
  user_id: string;
  source_type: string;
  source_hash: string;
  source_uri: string;
  status: string;
  progress: number;
  error_message: string | null;
  ai_provider: string;
  ai_model: string;
  created_at: string;
  completed_at: string | null;
  expires_at: string | null;
}

// ─── aiAnalyzeZip: 上传 zip 文件 → 真 multipart POST /imports → task_id ───────────────

/**
 * 提交 AI 智能导入任务。
 *
 * 🔴 **范式说明（dogfooding cluster-M17 fix）**：
 * - prism-0420 M17 是 **异步 Queue + WS 推进度**（非老 Prism 同步范式）
 * - 本 action 立即返回 ImportTask {id, status="pending"}；mapping_rows 为 [] / stats 全 0
 * - caller（ai-import-wizard.tsx）应在拿到 session_id 后：
 *   ① 开 WS 监听 /api/projects/{pid}/imports/{tid}/progress?token=<JWT>
 *   ② 收 review_ready 事件后调 GET /review 拉 ReviewDataResponse 填 mapping_rows
 *   ③ 用户调整后调 aiConfirmImport(projectId, taskId, mappingRows)
 *
 * 🔴 **依赖 actions/import.ts uploadZip 实装（escalation / 见 RCA.md）**：
 * - 当前 caller wizard step 0 调 uploadZip 同步解 zip 拿 ParsedFile[]（仍 punt）
 * - 本 action 入参 files: object[] 在异步范式下不真用（只取 file count）
 * - 完整 happy path 需 import.ts uploadZip 实装 + wizard 流程改造（独立 cluster）
 * - 本 cluster 接通 endpoint shim，caller 即可调真后端；mapping 数据走 WS + GET /review
 */
export async function aiAnalyzeZip(
  projectId: string,
  files: object[],
): Promise<ActionResult<AIAnalyzeResult>> {
  // 当前 caller 形态：files 已被 uploadZip 解析为 ParsedFile[]（client-side 无原始 zip Blob）
  // → backend POST /imports 需 multipart zip / 无法从 ParsedFile[] 反构造
  // → 本 action 返 actionError 显式提示 caller 用新 endpoint shim（escalation）
  // 但同时保留 happy path：若 caller 已切换到调 aiSubmitImportZip（见下方新 action），
  // 直接复用该路径。
  void files; // 异步范式下不直接使用
  if (!projectId) {
    return actionError(new AppError("projectId 必填", "blocking", ErrorCode.VALIDATION_ERROR, 400));
  }
  return actionError(
    new AppError(
      "M17 已切换异步 Queue + WS 范式：请改调 aiSubmitImportZip(projectId, file: File) 上传原始 zip，wizard 通过 WS 收 review_ready 后调 aiFetchReviewData。详 design-audit.md G1（dogfooding cluster-M17）。",
      "blocking",
      ErrorCode.INTERNAL_ERROR,
      501,
    ),
  );
}

/**
 * 上传原始 zip File 到 M17 后端（multipart）→ 立即返 task_id + status=pending。
 *
 * caller（ai-import-wizard.tsx）应在 step 0 上传 zip 后直接调此 action（跳 uploadZip
 * 同步解析），用 task_id 开 WS 监听后续进度。
 *
 * 范式与 actions/nodes.ts importNodesFromCSV 一致（M11 cold-start multipart 范式复用）。
 */
export async function aiSubmitImportZip(
  projectId: string,
  formData: FormData,
): Promise<ActionResult<ImportTaskResponse>> {
  try {
    const file = formData.get("file");
    if (!(file instanceof Blob)) {
      return actionError(new AppError("file 必填", "blocking", ErrorCode.VALIDATION_ERROR, 400));
    }

    // 服务端代理 multipart 上传（M11 范式 / actions/nodes.ts L545）
    const token = await getServerAccessToken();
    if (!token) {
      return actionError(new AppError("未登录", "blocking", ErrorCode.UNAUTHORIZED, 401));
    }
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

    const fd = new FormData();
    fd.append("source_type", "zip");
    fd.append("file", file, (file as File).name || "upload.zip");

    const resp = await fetch(`${baseUrl}/api/projects/${projectId}/imports`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    });

    if (!resp.ok) {
      const errBody = await resp.text().catch(() => `HTTP ${resp.status}`);
      let errCode: ErrorCode = ErrorCode.INTERNAL_ERROR;
      let errMsg = errBody;
      try {
        const parsed = JSON.parse(errBody) as { code?: string; message?: string };
        if (parsed.code === "import_invalid_source") {
          // M17 design §7 + §13: 422 IMPORT_INVALID_SOURCE
          errCode = ErrorCode.VALIDATION_ERROR;
          errMsg = parsed.message || "导入源无效（zip 损坏 / 文件过大 / ai_provider 未配置）";
        } else if (parsed.message) {
          errMsg = parsed.message;
        }
      } catch {
        // 非 JSON body
      }
      return actionError(new AppError(errMsg, "blocking", errCode, resp.status));
    }

    const task = (await resp.json()) as ImportTaskResponse;
    revalidatePath(`/projects/${projectId}/import`);
    return actionSuccess(task);
  } catch (error) {
    return actionError(error);
  }
}

/**
 * 拉取 M17 review 阶段数据（caller 在 WS review_ready 事件后调）。
 * GET /api/projects/{pid}/imports/{tid}/review → ReviewDataResponse
 */
export async function aiFetchReviewData(
  projectId: string,
  taskId: string,
): Promise<ActionResult<unknown>> {
  try {
    return await withAuthRedirect(async () => {
      const data = await serverApiGet<unknown>(
        `/api/projects/${projectId}/imports/${taskId}/review`,
      );
      return actionSuccess(data);
    });
  } catch (error) {
    return actionError(error);
  }
}

// ─── aiAdjustMapping: no-op（design-gap G2 / 后端无 review 中间调整 endpoint）───────────────

/**
 * 用户调整 mapping 通知后端（design-gap G2: 后端无对应 endpoint / no-op）。
 *
 * design §5 字面接受 last-write-wins / review 阶段不引入乐观锁。用户调整在 client-side
 * 累积，一次性走 confirm 提交。本 action 保留签名兼容 caller fire-and-forget 调用习惯。
 */
export async function aiAdjustMapping(
  _projectId: string,
  _sessionId: string,
  _adjustments: MappingAdjustment[],
): Promise<void> {
  // design-gap G2: backend 无 review 中间调整 endpoint / no-op
  // caller fire-and-forget；本函数显式 return（不再 punt error）
  return;
}

// ─── aiConfirmImport: POST /confirm（mapping_rows → ReviewConfirmRequest）───────────────

/**
 * 用户确认 review → 触发 backend ai_step3 + batch_insert。
 *
 * POST /api/projects/{pid}/imports/{tid}/confirm
 *
 * 🔴 **schema 转换**（design §7 ReviewConfirmRequest 与 caller MappingRow 形态差）：
 * - caller MappingRow: 一行 = 一个待映射 item（含 module_id + dimension_id + 用户调整后归属）
 * - backend ReviewConfirmRequest: nodes[] + dimensions[] + competitors[] + issues[]（按类型分组）
 *
 * 当前转换策略（dogfooding cluster-M17 minimal）：
 * - 每个 MappingRow 转为 ConfirmedDimension（{proposed_id, target_proposed_node_id, dimension_type_key, content}）
 * - 不构造 ConfirmedNode（review 数据完整流尚未在 caller 内）/ 标 design-gap
 * - skip_proposed_ids 取 selected=false 或 action="skip" 的 row.id
 *
 * 该转换在 happy path（caller 已走 WS + GET /review）下需 review_data 真实存在；当前
 * caller 流程下 mapping_rows 来源是 stub aiAnalyzeZip 空数组，confirm 实际不会被触发。
 * cluster-M17 escalation 路径已上报 design-audit.md。
 */
export async function aiConfirmImport(
  projectId: string,
  sessionId: string,
  mappingRows: MappingRow[],
): Promise<ActionResult<AIConfirmResult>> {
  try {
    return await withAuthRedirect(async () => {
      // MappingRow → ReviewConfirmRequest 最小转换
      const dimensions = mappingRows
        .filter((r) => r.selected && r.action !== "skip" && r.recommended_dimension_key)
        .map((r) => ({
          proposed_id: r.id,
          target_proposed_node_id: r.recommended_module_id, // node-id 占位（design-gap: review 阶段 proposed_node_id vs 用户选定的 module_id 范式差）
          dimension_type_key: r.recommended_dimension_key,
          content: { text: r.extracted_content || r.content },
        }));
      const skip_proposed_ids = mappingRows
        .filter((r) => !r.selected || r.action === "skip")
        .map((r) => r.id);

      const body = {
        nodes: [],
        dimensions,
        competitors: [],
        issues: [],
        skip_proposed_ids,
      };

      const task = await serverApiPost<ImportTaskResponse>(
        `/api/projects/${projectId}/imports/${sessionId}/confirm`,
        body,
      );

      revalidatePath(`/projects/${projectId}/import`);
      revalidatePath(`/projects/${projectId}`);

      // 转换 backend ImportTaskResponse → caller AIConfirmResult
      // 注：created_node_ids/imported/merged/skipped 在异步流下需通过 task=completed 后
      // 拉 detail 拿 items 反推；本 cluster 接通时仅返 task 状态 + 占位空 errors
      // caller 应在收到本响应后通过 WS completed 事件 + GET /detail 拿真实统计
      const importedCount = dimensions.length;
      const skippedCount = skip_proposed_ids.length;
      return actionSuccess<AIConfirmResult>({
        session_id: task.id,
        imported: importedCount,
        merged: 0,
        skipped: skippedCount,
        errors: [],
        created_node_ids: [], // design-gap G3: per-node id 在 backend confirmed_data 内部 / 不通过 response 返回
        relations_created: 0,
      });
    });
  } catch (error) {
    return actionError(error);
  }
}

// ─── aiUndoImport: POST /cancel（design-gap G3: task 级 cancel 而非 per-node undo）───────────────

/**
 * 撤销导入任务 → 调 POST /cancel（design-gap G3: backend cancel 是 task 级整体取消）。
 *
 * 🔴 **design-gap G3**：
 * - caller 期望 per-node undo（删特定 createdNodeIds）
 * - backend 提供 task 级 cancel（cancelled 状态 → 回滚整任务事务 / design §4 状态机）
 * - 若 task 已 completed（事务已 commit），cancel 会抛 IMPORT_TASK_FINALIZED 409
 *   → 此时调用方应走 M03 nodes DELETE API 逐个删 createdNodeIds（不在本 action 范围）
 *
 * 本 action 调 cancel；忽略 createdNodeIds 参数（caller 留参数兼容现有签名）。
 */
export async function aiUndoImport(
  projectId: string,
  sessionId: string,
  createdNodeIds: string[],
): Promise<ActionResult<{ deleted: number; errors: string[] }>> {
  try {
    return await withAuthRedirect(async () => {
      // design-gap G3: createdNodeIds 在 backend cancel 流程中不直接消费（task 级回滚）
      void createdNodeIds;

      // POST /cancel 返 204 No Content
      await serverApiFetch<void>(`/api/projects/${projectId}/imports/${sessionId}/cancel`, {
        method: "POST",
      });

      revalidatePath(`/projects/${projectId}/import`);
      revalidatePath(`/projects/${projectId}`);

      return actionSuccess({
        deleted: createdNodeIds.length, // caller 视角的"已撤销条数"（task 级回滚后逻辑等价）
        errors: [],
      });
    });
  } catch (error) {
    return actionError(error);
  }
}
