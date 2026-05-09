"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  serverApiGet,
  serverApiPost,
  serverApiPut,
  serverApiDelete,
  UnauthenticatedError,
} from "@/lib/server-http-client";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import { ErrorCode } from "@/lib/error-codes";
import {
  createNodeSchema,
  renameNodeSchema,
  deleteNodeSchema,
  createDimensionRecordSchema,
} from "@/lib/validators/node";
import { defineAction } from "@/lib/define-action";
import type { components } from "@/types/api";

type NodeResponse = components["schemas"]["NodeResponse"];
type NodeWithChildren = components["schemas"]["NodeWithChildrenResponse"];
type NodeOverview = components["schemas"]["NodeOverview"];
type OverviewResponse = components["schemas"]["OverviewResponse"];
type NodeCreate = components["schemas"]["NodeCreate"];
type NodeUpdate = components["schemas"]["NodeUpdate"];
type NodeMove = components["schemas"]["NodeMove"];
type NodeReorder = components["schemas"]["NodeReorder"];
type DimensionConfigListResponse = components["schemas"]["DimensionConfigListResponse"];
type DimensionConfigResponse = components["schemas"]["DimensionConfigResponse"];
type DimensionListResponse = components["schemas"]["DimensionListResponse"];
type DimensionResponse = components["schemas"]["DimensionResponse"];
type DimensionCreate = components["schemas"]["DimensionCreate"];
type DimensionUpdate = components["schemas"]["DimensionUpdate"];
type VersionListResponse = components["schemas"]["VersionListResponse"];

/**
 * spec 06 §3 字面：Server-side read action 401 → redirect /login。
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

interface TreeNode extends NodeWithChildren {
  children: TreeNode[];
  completionPercent: number;
}

/**
 * 项目节点树 + 完善度（M16 overview）。
 * 走 /api/projects/{pid}/overview 端点（NodeOverview 已含 completion_rate / 后端已计算）。
 * 返回 shape 与拷贝层旧 drizzle 版本兼容（含 completionPercent + children 嵌套）。
 */
export async function getProjectTree(projectId: string): Promise<TreeNode[]> {
  return withAuthRedirect(async () => {
    const data = await serverApiGet<OverviewResponse>(`/api/projects/${projectId}/overview`);
    return data.tree.map((n) => overviewToTreeNode(n, projectId));
  });
}

function overviewToTreeNode(node: NodeOverview, projectId: string): TreeNode {
  return {
    id: node.id,
    project_id: projectId,
    parent_id: node.parent_id,
    name: node.name,
    description: null,
    type: node.type,
    depth: node.depth,
    sort_order: node.sort_order,
    path: node.path,
    created_by: null,
    updated_by: null,
    created_at: "",
    updated_at: "",
    children: node.children.map((c) => overviewToTreeNode(c, projectId)),
    completionPercent: Math.round(node.completion_rate * 100),
  };
}

export async function getNodeWithDimensions(nodeId: string, projectId: string) {
  return withAuthRedirect(async () => {
    try {
      const node = await serverApiGet<NodeResponse>(`/api/projects/${projectId}/nodes/${nodeId}`);
      const dims = await serverApiGet<DimensionListResponse>(
        `/api/projects/${projectId}/nodes/${nodeId}/dimensions`,
      );
      const versions = await serverApiGet<VersionListResponse>(
        `/api/projects/${projectId}/nodes/${nodeId}/versions`,
      );
      return {
        node,
        records: dims.items.map((r) => ({
          record: r,
          dimType: dims.enabled_dimension_types.find((t) => t.id === r.dimension_type_id) ?? null,
        })),
        versions: versions.items,
      };
    } catch (error) {
      if (error instanceof UnauthenticatedError) throw error;
      return null;
    }
  });
}

export async function getProjectDimensions(projectId: string): Promise<DimensionConfigResponse[]> {
  return withAuthRedirect(async () => {
    const data = await serverApiGet<DimensionConfigListResponse>(
      `/api/projects/${projectId}/dimension-configs`,
    );
    return data.items;
  });
}

export const createNode = defineAction(
  createNodeSchema,
  async ({ projectId, parentId, name, type }): Promise<ActionResult<{ id: string }>> => {
    try {
      const body: NodeCreate = {
        name,
        type,
        parent_id: parentId ?? null,
      };
      const newNode = await serverApiPost<NodeResponse>(`/api/projects/${projectId}/nodes`, body);
      logger.action("node.create", "self", { projectId, nodeId: newNode.id, type });
      revalidatePath(`/projects/${projectId}`);
      return actionSuccess({ id: newNode.id });
    } catch (error) {
      return actionError(error);
    }
  },
);

export const createDimensionRecord = defineAction(
  createDimensionRecordSchema,
  async ({
    nodeId,
    dimensionTypeId,
    content,
    projectId,
  }): Promise<ActionResult<{ id: string }>> => {
    try {
      const body: DimensionCreate = {
        dimension_type_id: dimensionTypeId,
        content,
      };
      const record = await serverApiPost<DimensionResponse>(
        `/api/projects/${projectId}/nodes/${nodeId}/dimensions`,
        body,
      );
      logger.action("dimension.create", "self", { nodeId, dimensionTypeId });
      revalidatePath(`/projects/${projectId}`);
      return actionSuccess({ id: record.id });
    } catch (error) {
      return actionError(error);
    }
  },
);

export async function updateDimensionRecord(
  recordId: string,
  content: Record<string, unknown>,
  expectedVersion: number,
  projectId: string,
  nodeId: string,
  dimensionTypeId: number,
): Promise<ActionResult<{ id: string; version: number }>> {
  try {
    const body: DimensionUpdate = {
      content,
      expected_version: expectedVersion,
    };
    const updated = await serverApiPut<DimensionResponse>(
      `/api/projects/${projectId}/nodes/${nodeId}/dimensions/${dimensionTypeId}`,
      body,
    );
    if (updated.id !== recordId) {
      logger.action("dimension.update.id-shift", "self", {
        recordId,
        actualId: updated.id,
      });
    }
    logger.action("dimension.update", "self", {
      recordId: updated.id,
      newVersion: updated.version,
    });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess({ id: updated.id, version: updated.version });
  } catch (error) {
    return actionError(error);
  }
}

export async function deleteDimensionRecord(
  recordId: string,
  projectId: string,
  nodeId: string,
  dimensionTypeId: number,
): Promise<ActionResult> {
  try {
    await serverApiDelete(
      `/api/projects/${projectId}/nodes/${nodeId}/dimensions/${dimensionTypeId}`,
    );
    logger.action("dimension.delete", "self", { recordId });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export const renameNode = defineAction(
  renameNodeSchema,
  async ({ nodeId, name: newName, projectId }): Promise<ActionResult> => {
    try {
      const body: NodeUpdate = { name: newName };
      await serverApiPut<NodeResponse>(`/api/projects/${projectId}/nodes/${nodeId}`, body);
      logger.action("node.rename", "self", { nodeId, newName });
      revalidatePath(`/projects/${projectId}`);
      return actionSuccess(undefined);
    } catch (error) {
      return actionError(error);
    }
  },
);

export const deleteNode = defineAction(
  deleteNodeSchema,
  async ({ nodeId, projectId }): Promise<ActionResult> => {
    try {
      await serverApiDelete(`/api/projects/${projectId}/nodes/${nodeId}`);
      logger.action("node.delete", "self", { nodeId, projectId });
      revalidatePath(`/projects/${projectId}`);
      return actionSuccess(undefined);
    } catch (error) {
      return actionError(error);
    }
  },
);

/**
 * 文件夹下层级总览（拷贝层 workspace.tsx 消费）。
 * 后端无单端点；通过 /overview 取整树后切片返回直接子节点。
 */
export async function getFolderOverview(folderNodeId: string, projectId: string) {
  return withAuthRedirect(async () => {
    const overview = await serverApiGet<OverviewResponse>(`/api/projects/${projectId}/overview`);
    const folder = findInTree(overview.tree, folderNodeId);
    if (!folder) return [];
    const dimCount = overview.stats.enabled_dimension_count;
    return folder.children.map((child) => ({
      id: child.id,
      project_id: projectId,
      parent_id: child.parent_id,
      name: child.name,
      description: null,
      type: child.type,
      depth: child.depth,
      sort_order: child.sort_order,
      path: child.path,
      created_by: null,
      updated_by: null,
      created_at: "",
      updated_at: "",
      filledDimensions: child.filled_count,
      totalDimensions: dimCount,
      completionPercent: Math.round(child.completion_rate * 100),
      childCount: child.children.length,
    }));
  });
}

function findInTree(tree: NodeOverview[], id: string): NodeOverview | null {
  for (const n of tree) {
    if (n.id === id) return n;
    const sub = findInTree(n.children, id);
    if (sub) return sub;
  }
  return null;
}

/**
 * 节点子孙数 / 维度记录数（删除前确认）。后端无单端点；从 /overview 派生 + dimensions 列表。
 */
export async function getNodeDescendantCount(
  nodeId: string,
  projectId: string,
): Promise<{ childNodeCount: number; dimensionRecordCount: number } | null> {
  return withAuthRedirect(async () => {
    try {
      const overview = await serverApiGet<OverviewResponse>(`/api/projects/${projectId}/overview`);
      const node = findInTree(overview.tree, nodeId);
      if (!node) return null;

      const ids: string[] = [];
      const walk = (n: NodeOverview) => {
        if (n.id !== nodeId) ids.push(n.id);
        n.children.forEach(walk);
      };
      walk(node);

      let dimCount = 0;
      const allIds = [nodeId, ...ids];
      const results = await Promise.all(
        allIds.map((id) =>
          serverApiGet<DimensionListResponse>(
            `/api/projects/${projectId}/nodes/${id}/dimensions`,
          ).catch(() => null),
        ),
      );
      for (const r of results) {
        if (r) dimCount += r.items.length;
      }

      return { childNodeCount: ids.length, dimensionRecordCount: dimCount };
    } catch (error) {
      if (error instanceof UnauthenticatedError) throw error;
      return null;
    }
  });
}

/**
 * 同级排序（拷贝层 workspace.tsx 单节点位置切换）。
 * 后端 /nodes/reorder 是批量端点 / 此处先取兄弟列表 → 重排序 → 全量提交。
 */
export async function updateNodeSortOrder(
  nodeId: string,
  newSortOrder: number,
  projectId: string,
): Promise<ActionResult> {
  try {
    const node = await serverApiGet<NodeResponse>(`/api/projects/${projectId}/nodes/${nodeId}`);
    const overview = await serverApiGet<OverviewResponse>(`/api/projects/${projectId}/overview`);
    const parent = node.parent_id ? findInTree(overview.tree, node.parent_id) : null;
    const siblings = parent ? parent.children : overview.tree;
    const sorted = [...siblings].sort((a, b) => a.sort_order - b.sort_order);
    const oldIdx = sorted.findIndex((s) => s.id === nodeId);
    if (oldIdx === -1) {
      return actionError(new AppError("节点未找到", "blocking", "NOT_FOUND", 404));
    }
    const target = sorted[oldIdx];
    sorted.splice(oldIdx, 1);
    sorted.splice(newSortOrder, 0, target);

    const body: NodeReorder = {
      parent_id: node.parent_id ?? null,
      items: sorted.map((s, idx) => ({ node_id: s.id, sort_order: idx })),
    };
    await serverApiPost(`/api/projects/${projectId}/nodes/reorder`, body);
    logger.action("node.reorder", "self", { nodeId, newSortOrder });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function moveNode(
  nodeId: string,
  newParentId: string | null,
  projectId: string,
): Promise<ActionResult> {
  try {
    if (newParentId === nodeId) {
      return actionError(
        new AppError("不能将节点移动到自身下", "blocking", "VALIDATION_ERROR", 400),
      );
    }
    const body: NodeMove = { new_parent_id: newParentId };
    await serverApiPost(`/api/projects/${projectId}/nodes/${nodeId}/move`, body);
    logger.action("node.move", "self", { nodeId, newParentId, projectId });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

/**
 * 模块关系（拷贝层 relation-graph 消费）— 此函数移到 actions/relations.ts getRelationGraph；
 * 保留 stub 以防消费方仍直接 import；返回空数据 + 错误码。
 *
 * 注：当前消费者 `app/projects/[projectId]/relation-graph/page.tsx` 已 import getRelationGraph
 * （来自 relations.ts）/ 此 stub 在 ignore 下不破。
 */
export async function getModuleRelations(projectId: string) {
  void projectId;
  return { nodes: [], edges: [] };
}

/**
 * 竞品维度记录（拷贝层 comparison/page.tsx 消费）。
 * 后端：M06 competitor-refs 端点（在子片 3c 接入）/ 本子片 punt：返回空 + 标 punt。
 * 拷贝层 comparison page 仍在 eslint ignore 内 / 不破 lint。
 */
export async function getCompetitiveRecords(projectId: string) {
  void projectId;
  return [];
}

/**
 * CSV 导入（拷贝层 import-csv-modal 消费）。
 * 后端 M11 cold-start 端点 = `/api/projects/{pid}/cold-start/upload` (multipart) → 异步任务。
 * 旧签名 `(projectId, csvContent: string)` → 重塑为内部包装：将 CSV string 包成 Blob 走 multipart。
 * 完整异步流程（task_id 轮询 / status 处理）由 actions/import.ts 接管 / 本函数仅提交。
 */
export async function importNodesFromCSV(
  projectId: string,
  csvContent: string,
): Promise<ActionResult<{ imported: number; errors: string[] }>> {
  try {
    const fd = new FormData();
    const blob = new Blob([csvContent], { type: "text/csv" });
    fd.append("file", blob, "import.csv");

    // 服务端代理上传：手动 fetch（multipart 不能走 serverApiFetch JSON 序列化）
    const { getServerAccessToken } = await import("@/lib/server-auth");
    const token = await getServerAccessToken();
    if (!token) {
      redirect("/login");
    }
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const resp = await fetch(`${baseUrl}/api/projects/${projectId}/cold-start/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    });
    if (!resp.ok) {
      const detail = await resp.text().catch(() => `HTTP ${resp.status}`);
      return actionError(
        new AppError(detail || "CSV 上传失败", "blocking", ErrorCode.INTERNAL_ERROR, resp.status),
      );
    }
    const data = (await resp.json()) as {
      task_id?: string;
      imported?: number;
      errors?: string[];
    };
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess({
      imported: data.imported ?? 0,
      errors: data.errors ?? (data.task_id ? [`任务已提交 (task_id: ${data.task_id})`] : []),
    });
  } catch (error) {
    return actionError(error);
  }
}
