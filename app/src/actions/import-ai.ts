"use server";

import { revalidatePath } from "next/cache";
import { requireAuth } from "@/lib/auth";
import { checkProjectAccess } from "@/services/permission.service";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import { ErrorCode } from "@/lib/error-codes";
import { logActivity } from "./activity-log";

const API_BASE = process.env.API_URL ?? "http://localhost:8001";
const INTERNAL_TOKEN = process.env.INTERNAL_TOKEN ?? "";

// ─── Types ───────────────────────────────────────────────────────────────────

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

// ─── AI Analyze (calls FastAPI) ──────────────────────────────────────────────

export async function aiAnalyzeZip(
  projectId: string,
  files: object[],
): Promise<ActionResult<AIAnalyzeResult>> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "editor");

    if (!files.length) {
      return actionError(new AppError("文件列表不能为空", "blocking", "VALIDATION_ERROR", 400));
    }

    const res = await fetch(`${API_BASE}/api/import/ai-analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-User-Id": user.id,
      },
      body: JSON.stringify({
        project_id: projectId,
        user_id: user.id,
        files,
      }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: "AI分析失败" }));
      return actionError(
        new AppError(body.detail || "AI分析失败", "blocking", ErrorCode.INTERNAL_ERROR, res.status),
      );
    }

    const data: AIAnalyzeResult = await res.json();

    logger.action("import.ai_analyze", user.id, {
      projectId,
      totalItems: data.stats.total_items,
      conflicts: data.stats.conflicts,
    });

    return actionSuccess(data);
  } catch (error) {
    return actionError(error);
  }
}

// ─── AI Adjust Mapping ───────────────────────────────────────────────────────

export interface MappingAdjustment {
  id: string;
  recommended_module_id: string;
  recommended_dimension_id: number | null;
}

export async function aiAdjustMapping(
  projectId: string,
  sessionId: string,
  adjustments: MappingAdjustment[],
): Promise<void> {
  // Fire-and-forget: persist mapping adjustments; errors are non-blocking
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "editor");

    await fetch(`${API_BASE}/api/import/ai-mapping`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-User-Id": user.id,
      },
      body: JSON.stringify({
        session_id: sessionId,
        project_id: projectId,
        adjustments,
      }),
    });
  } catch {
    // Non-blocking; local state is the source of truth
  }
}

// ─── AI Confirm Import ───────────────────────────────────────────────────────

export async function aiConfirmImport(
  projectId: string,
  sessionId: string,
  mappingRows: MappingRow[],
): Promise<ActionResult<AIConfirmResult>> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "editor");

    if (!mappingRows.length) {
      return actionError(new AppError("没有要导入的项目", "blocking", "VALIDATION_ERROR", 400));
    }

    const res = await fetch(`${API_BASE}/api/import/ai-confirm`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-User-Id": user.id,
      },
      body: JSON.stringify({
        session_id: sessionId,
        project_id: projectId,
        user_id: user.id,
        mapping_rows: mappingRows,
      }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: "导入失败" }));
      return actionError(
        new AppError(body.detail || "导入失败", "blocking", ErrorCode.INTERNAL_ERROR, res.status),
      );
    }

    const data: AIConfirmResult = await res.json();

    logger.action("import.ai_confirm", user.id, {
      projectId,
      sessionId,
      imported: data.imported,
      merged: data.merged,
      skipped: data.skipped,
      errors: data.errors.length,
    });

    await logActivity({
      projectId,
      userId: user.id,
      actionType: "ai_import",
      targetType: "project",
      targetId: projectId,
      summary: `AI智能导入完成：导入${data.imported}个，合并${data.merged}个，跳过${data.skipped}个`,
      metadata: {
        session_id: sessionId,
        imported: data.imported,
        merged: data.merged,
        skipped: data.skipped,
        error_count: data.errors.length,
        relations_created: data.relations_created,
      },
    });

    revalidatePath(`/projects/${projectId}`);

    return actionSuccess(data);
  } catch (error) {
    return actionError(error);
  }
}

// ─── AI Undo Import ───────────────────────────────────────────────────────────

export async function aiUndoImport(
  projectId: string,
  sessionId: string,
  createdNodeIds: string[],
): Promise<ActionResult<{ deleted: number; errors: string[] }>> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "editor");

    if (!createdNodeIds.length) {
      return actionError(new AppError("没有可撤销的导入记录", "blocking", "VALIDATION_ERROR", 400));
    }

    const res = await fetch(`${API_BASE}/api/import/undo`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-User-Id": user.id,
      },
      body: JSON.stringify({
        session_id: sessionId,
        project_id: projectId,
        user_id: user.id,
        created_node_ids: createdNodeIds,
      }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: "撤销失败" }));
      return actionError(
        new AppError(body.detail || "撤销失败", "blocking", ErrorCode.INTERNAL_ERROR, res.status),
      );
    }

    const data = await res.json();

    logger.action("import.ai_undo", user.id, {
      projectId,
      sessionId,
      deleted: data.deleted,
    });

    await logActivity({
      projectId,
      userId: user.id,
      actionType: "ai_import_undo",
      targetType: "project",
      targetId: projectId,
      summary: `AI导入已撤销：删除${data.deleted}个功能项`,
      metadata: { session_id: sessionId, deleted: data.deleted },
    });

    revalidatePath(`/projects/${projectId}`);

    return actionSuccess(data);
  } catch (error) {
    return actionError(error);
  }
}
