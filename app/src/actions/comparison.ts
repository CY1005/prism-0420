"use server";

import { revalidatePath } from "next/cache";
import {
  serverApiGet,
  serverApiPost,
  serverApiPut,
  serverApiDelete,
} from "@/lib/server-http-client";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess } from "@/lib/errors";
import { defineAction } from "@/lib/define-action";
import { createSnapshotSchema, renameSnapshotSchema } from "@/lib/validators/comparison";
import type { components } from "@/types/api";
import { withAuthRedirect } from "@/lib/server-action-helpers";

/**
 * M12 功能对比矩阵 server actions —
 * design/02-modules/M12-comparison/00-design.md §6 + §7（6 endpoints / 单 router 前缀
 * `/api/projects/{project_id}/comparison`）。
 *
 * 6 endpoints (api/routers/comparison_router.py 字面真名):
 *   GET    /matrix                         viewer  → ComparisonMatrixResponse (cells-only / R-X3)
 *   GET    /snapshots                      viewer  → SnapshotListResponse (按 created_at 倒序)
 *   GET    /snapshots/{snapshot_id}        viewer  → SnapshotDetailResponse (含 items)
 *   POST   /snapshots                      editor  → SnapshotResponse (201) + activity_log create
 *   PUT    /snapshots/{snapshot_id}        editor  → SnapshotResponse (含乐观锁 expected_version)
 *   DELETE /snapshots/{snapshot_id}        editor  → 204 + items 级联删除 + activity_log delete
 *
 * tenant：路径 `/api/projects/{project_id}/...` 自带 / 所有 caller 必传 projectId / Router 端 check_project_access。
 * idempotency：M12 design §11 显式无（创建快照天然唯一 / rename 走乐观锁 / DELETE 自然幂等）。
 * 与 actions/analyze.ts 关系：analyze.ts 中的 generateComparisonAction / backfillRowAction /
 * exportComparisonAction 是 prism v1 拷贝层 stub（puntResult / 接 M13 analyze 端点而非 M12），
 * cluster-M12 后 comparison/page.tsx 不再 import 它们；这 3 个 stub 仍留 actions/analyze.ts 不删
 * （M13 cluster 单独决定其归宿 / 守 cluster boundary / 不破其他 caller）。
 */

type ComparisonMatrixResponse = components["schemas"]["ComparisonMatrixResponse"];
type MatrixCell = components["schemas"]["MatrixCell"];
type SnapshotResponse = components["schemas"]["SnapshotResponse"];
type SnapshotDetailResponse = components["schemas"]["SnapshotDetailResponse"];
type SnapshotListResponse = components["schemas"]["SnapshotListResponse"];
type SnapshotCreateRequest = components["schemas"]["SnapshotCreateRequest"];
type SnapshotUpdateRequest = components["schemas"]["SnapshotUpdateRequest"];

export type {
  ComparisonMatrixResponse,
  MatrixCell,
  SnapshotResponse,
  SnapshotDetailResponse,
  SnapshotListResponse,
};

// ─── Read ───────────────────────────────────────────────────────────────────

/**
 * 实时矩阵渲染（design §7 cells-only / R-X3 不嵌跨模块 metadata）。
 * 节点 / 维度 metadata 由前端独立从 getProjectTree + getProjectDimensions 拼装。
 */
export async function getMatrix(
  projectId: string,
  nodeIds: string[],
  dimensionTypeIds: number[],
): Promise<ComparisonMatrixResponse> {
  return withAuthRedirect(async () => {
    const qs = new URLSearchParams();
    nodeIds.forEach((id) => qs.append("node_ids", id));
    dimensionTypeIds.forEach((id) => qs.append("dimension_type_ids", String(id)));
    return serverApiGet<ComparisonMatrixResponse>(
      `/api/projects/${projectId}/comparison/matrix?${qs.toString()}`,
    );
  });
}

export async function listSnapshots(projectId: string, limit = 50): Promise<SnapshotListResponse> {
  return withAuthRedirect(async () => {
    return serverApiGet<SnapshotListResponse>(
      `/api/projects/${projectId}/comparison/snapshots?limit=${limit}`,
    );
  });
}

export async function getSnapshotDetail(
  projectId: string,
  snapshotId: string,
): Promise<SnapshotDetailResponse> {
  return withAuthRedirect(async () => {
    return serverApiGet<SnapshotDetailResponse>(
      `/api/projects/${projectId}/comparison/snapshots/${snapshotId}`,
    );
  });
}

// ─── Write ──────────────────────────────────────────────────────────────────

export const createSnapshot = defineAction(
  createSnapshotSchema,
  async ({
    projectId,
    name,
    description,
    nodeIds,
    dimensionTypeIds,
  }): Promise<ActionResult<{ id: string; version: number }>> => {
    const body: SnapshotCreateRequest = {
      name,
      description: description ?? null,
      node_ids: nodeIds,
      dimension_type_ids: dimensionTypeIds,
    };
    const snap = await serverApiPost<SnapshotResponse>(
      `/api/projects/${projectId}/comparison/snapshots`,
      body,
    );
    logger.action("comparison.snapshot.create", "self", {
      projectId,
      snapshotId: snap.id,
      nodes: nodeIds.length,
      dimensions: dimensionTypeIds.length,
    });
    revalidatePath(`/projects/${projectId}/comparison`);
    return actionSuccess({ id: snap.id, version: snap.version });
  },
);

export const renameSnapshot = defineAction(
  renameSnapshotSchema,
  async ({
    projectId,
    snapshotId,
    name,
    description,
    expectedVersion,
  }): Promise<ActionResult<{ id: string; version: number }>> => {
    const body: SnapshotUpdateRequest = {
      name,
      description: description ?? null,
      expected_version: expectedVersion,
    };
    const snap = await serverApiPut<SnapshotResponse>(
      `/api/projects/${projectId}/comparison/snapshots/${snapshotId}`,
      body,
    );
    logger.action("comparison.snapshot.rename", "self", {
      snapshotId,
      newVersion: snap.version,
    });
    revalidatePath(`/projects/${projectId}/comparison`);
    return actionSuccess({ id: snap.id, version: snap.version });
  },
);

export async function deleteSnapshot(projectId: string, snapshotId: string): Promise<ActionResult> {
  try {
    await serverApiDelete(`/api/projects/${projectId}/comparison/snapshots/${snapshotId}`);
    logger.action("comparison.snapshot.delete", "self", { snapshotId, projectId });
    revalidatePath(`/projects/${projectId}/comparison`);
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}
