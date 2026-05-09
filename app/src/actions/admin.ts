"use server";

/* eslint-disable @typescript-eslint/no-unused-vars -- 子片 3c：用户管理 4 函数 NOT_IMPLEMENTED stub（prism-0420 OpenAPI 暂未提供 admin 用户管理域 / 子片 5 后或 Phase 2.3 评估接入） */
import { redirect } from "next/navigation";
import { serverApiGet, serverApiPost, UnauthenticatedError } from "@/lib/server-http-client";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess } from "@/lib/errors";
import type { components } from "@/types/api";

type EmbeddingStatsResponse = components["schemas"]["EmbeddingStatsResponse"];
type BackfillRequest = components["schemas"]["BackfillRequest"];
type BackfillResponse = components["schemas"]["BackfillResponse"];
type ModelUpgradeRequest = components["schemas"]["ModelUpgradeRequest"];
type ModelUpgradeResponse = components["schemas"]["ModelUpgradeResponse"];

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

/**
 * prism-0420 admin endpoint：embedding 域（M18 / platform_admin only）。
 * 用户管理（旧 getUsers / createUser / toggleUserStatus / updateUserRole）在 prism-0420 OpenAPI 无对应路径，
 * 子片 3c punt：保留为 NOT_IMPLEMENTED stub，等后端补 admin 用户管理域 / 子片 5+ 或 Phase 2.3。
 */

export async function getEmbeddingStats(): Promise<EmbeddingStatsResponse> {
  return withAuthRedirect(async () => {
    return await serverApiGet<EmbeddingStatsResponse>("/api/admin/embedding/stats");
  });
}

export async function triggerBackfill(
  payload: BackfillRequest,
): Promise<ActionResult<BackfillResponse>> {
  try {
    const data = await serverApiPost<BackfillResponse>("/api/admin/embedding/backfill", payload);
    logger.action("admin.embeddingBackfill", "self", { projectId: payload.project_id });
    return actionSuccess(data);
  } catch (error) {
    return actionError(error);
  }
}

export async function triggerModelUpgrade(
  payload: ModelUpgradeRequest,
): Promise<ActionResult<ModelUpgradeResponse>> {
  try {
    const data = await serverApiPost<ModelUpgradeResponse>(
      "/api/admin/embedding/model-upgrade",
      payload,
    );
    logger.action("admin.embeddingModelUpgrade", "self", { projectId: payload.project_id });
    return actionSuccess(data);
  } catch (error) {
    return actionError(error);
  }
}

const NOT_IMPLEMENTED = new Error(
  "admin 用户管理 endpoint 在 prism-0420 OpenAPI 暂未提供（子片 5 后或 Phase 2.3）",
);

export async function getUsers(): Promise<never[]> {
  return [];
}

export async function createUser(
  _name: string,
  _email: string,
  _password: string,
): Promise<ActionResult<{ id: string }>> {
  return actionError(NOT_IMPLEMENTED);
}

export async function toggleUserStatus(_userId: string): Promise<ActionResult> {
  return actionError(NOT_IMPLEMENTED);
}

export async function updateUserRole(_userId: string, _role: string): Promise<ActionResult> {
  return actionError(NOT_IMPLEMENTED);
}
