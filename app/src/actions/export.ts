"use server";

import { requireAuth } from "@/lib/auth";
import { checkProjectAccess } from "@/services/permission.service";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import { ErrorCode } from "@/lib/error-codes";

const API_BASE = process.env.API_URL ?? "http://localhost:8001";
const INTERNAL_TOKEN = process.env.INTERNAL_TOKEN ?? "";

// ─── exportNodes ─────────────────────────────────────

export async function exportNodes(
  projectId: string,
  nodeIds: string[],
): Promise<ActionResult<{ filename: string; content: string }>> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "viewer");

    if (!nodeIds.length) {
      return actionError(new AppError("请选择要导出的节点", "blocking", "VALIDATION_ERROR"));
    }

    const res = await fetch(`${API_BASE}/api/export/nodes`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-User-Id": user.id,
      },
      body: JSON.stringify({
        project_id: projectId,
        node_ids: nodeIds,
      }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: "导出失败" }));
      return actionError(
        new AppError(body.detail || "导出失败", "blocking", ErrorCode.INTERNAL_ERROR, res.status),
      );
    }

    const data = await res.json();

    logger.action("export.nodes", user.id, {
      projectId,
      nodeCount: nodeIds.length,
    });

    return actionSuccess({
      filename: data.filename,
      content: data.content,
    });
  } catch (error) {
    return actionError(error);
  }
}

// ─── exportProject ───────────────────────────────────

export async function exportProject(
  projectId: string,
  productLineId?: string,
): Promise<ActionResult<{ filename: string; content: string }>> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "viewer");

    const res = await fetch(`${API_BASE}/api/export/project`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-User-Id": user.id,
      },
      body: JSON.stringify({
        project_id: projectId,
        ...(productLineId && { product_line_id: productLineId }),
      }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: "导出失败" }));
      return actionError(
        new AppError(body.detail || "导出失败", "blocking", ErrorCode.INTERNAL_ERROR, res.status),
      );
    }

    // Convert zip binary to base64 for transport
    const arrayBuf = await res.arrayBuffer();
    const base64 = Buffer.from(arrayBuf).toString("base64");

    logger.action("export.project", user.id, {
      projectId,
      productLineId,
    });

    return actionSuccess({
      filename: "project_export.zip",
      content: base64,
    });
  } catch (error) {
    return actionError(error);
  }
}
