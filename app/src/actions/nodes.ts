"use server";

import { db } from "@/db";
import {
  nodes,
  dimensionRecords,
  versionRecords,
  dimensionTypes,
  projectDimensionConfigs,
  nodeRelations,
} from "@/db/schema";
import { eq, and, asc, isNull, inArray, or, sql, like } from "drizzle-orm";
import { revalidatePath } from "next/cache";
import { requireAuth } from "@/lib/auth";
import { checkProjectAccess } from "@/services/permission.service";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import { ErrorCode } from "@/lib/error-codes";
import { defineAction } from "@/lib/define-action";
import {
  createNodeSchema,
  renameNodeSchema,
  deleteNodeSchema,
  createDimensionRecordSchema,
} from "@/lib/validators/node";
import { logActivity } from "./activity-log";

export async function getProjectTree(projectId: string) {
  const user = await requireAuth();
  await checkProjectAccess(user.id, projectId, "viewer");

  const allNodes = await db
    .select()
    .from(nodes)
    .where(eq(nodes.projectId, projectId))
    .orderBy(asc(nodes.depth), asc(nodes.sortOrder));

  const dimConfigs = await db
    .select()
    .from(projectDimensionConfigs)
    .where(
      and(
        eq(projectDimensionConfigs.projectId, projectId),
        eq(projectDimensionConfigs.enabled, true),
      ),
    );
  const totalDims = dimConfigs.length;

  const allRecords = await db
    .select({
      nodeId: dimensionRecords.nodeId,
      dimTypeId: dimensionRecords.dimensionTypeId,
    })
    .from(dimensionRecords)
    .innerJoin(nodes, eq(dimensionRecords.nodeId, nodes.id))
    .where(eq(nodes.projectId, projectId));

  const filledPerNode = new Map<string, Set<number>>();
  for (const r of allRecords) {
    if (!filledPerNode.has(r.nodeId)) filledPerNode.set(r.nodeId, new Set());
    filledPerNode.get(r.nodeId)!.add(r.dimTypeId);
  }

  type TreeNode = (typeof allNodes)[number] & {
    children: TreeNode[];
    completionPercent: number;
  };
  const nodeMap = new Map<string, TreeNode>();
  const roots: TreeNode[] = [];

  for (const node of allNodes) {
    const filled = filledPerNode.get(node.id)?.size ?? 0;
    const percent = totalDims > 0 ? Math.round((filled / totalDims) * 100) : 0;
    nodeMap.set(node.id, {
      ...node,
      children: [],
      completionPercent: node.type === "file" ? percent : 0,
    });
  }

  for (const node of allNodes) {
    const treeNode = nodeMap.get(node.id)!;
    if (node.parentId) {
      const parent = nodeMap.get(node.parentId);
      if (parent) parent.children.push(treeNode);
    } else {
      roots.push(treeNode);
    }
  }

  function calcFolderCompletion(node: TreeNode): number {
    if (node.type === "file") return node.completionPercent;
    if (node.children.length === 0) return 0;
    const sum = node.children.reduce((acc, c) => acc + calcFolderCompletion(c), 0);
    node.completionPercent = Math.round(sum / node.children.length);
    return node.completionPercent;
  }
  roots.forEach(calcFolderCompletion);

  return roots;
}

export async function getNodeWithDimensions(nodeId: string) {
  const user = await requireAuth();

  const [node] = await db.select().from(nodes).where(eq(nodes.id, nodeId));
  if (!node) return null;

  await checkProjectAccess(user.id, node.projectId, "viewer");

  const records = await db
    .select({
      record: dimensionRecords,
      dimType: dimensionTypes,
    })
    .from(dimensionRecords)
    .innerJoin(dimensionTypes, eq(dimensionRecords.dimensionTypeId, dimensionTypes.id))
    .where(eq(dimensionRecords.nodeId, nodeId));

  const versions = await db
    .select()
    .from(versionRecords)
    .where(eq(versionRecords.nodeId, nodeId))
    .orderBy(asc(versionRecords.createdAt));

  return { node, records, versions };
}

export async function getProjectDimensions(projectId: string) {
  const user = await requireAuth();
  await checkProjectAccess(user.id, projectId, "viewer");

  return db
    .select({
      config: projectDimensionConfigs,
      dimType: dimensionTypes,
    })
    .from(projectDimensionConfigs)
    .innerJoin(dimensionTypes, eq(projectDimensionConfigs.dimensionTypeId, dimensionTypes.id))
    .where(
      and(
        eq(projectDimensionConfigs.projectId, projectId),
        eq(projectDimensionConfigs.enabled, true),
      ),
    )
    .orderBy(asc(projectDimensionConfigs.sortOrder));
}

export const createNode = defineAction(
  createNodeSchema,
  async ({ projectId, parentId, name, type }): Promise<ActionResult<{ id: string }>> => {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "editor");

    const parent = parentId
      ? (await db.select().from(nodes).where(eq(nodes.id, parentId)))[0]
      : null;

    const depth = parent ? parent.depth + 1 : 0;
    const path = parent ? (parent.path ? `${parent.path}/${parent.id}` : parent.id) : "";

    const siblings = parentId
      ? await db
          .select()
          .from(nodes)
          .where(and(eq(nodes.projectId, projectId), eq(nodes.parentId, parentId)))
      : await db
          .select()
          .from(nodes)
          .where(and(eq(nodes.projectId, projectId), isNull(nodes.parentId)));

    const sortOrder = siblings.length;

    const [newNode] = await db
      .insert(nodes)
      .values({
        projectId,
        parentId,
        name,
        type,
        depth,
        sortOrder,
        path,
        createdBy: user.id,
      })
      .returning();

    logger.action("node.create", user.id, {
      projectId,
      nodeId: newNode.id,
      type,
    });
    logActivity({
      projectId,
      userId: user.id,
      actionType: "create",
      targetType: "node",
      targetId: newNode.id,
      summary: `创建${type === "folder" ? "文件夹" : "功能项"} "${name}"`,
    });
    revalidatePath(`/projects/${projectId}`);

    return actionSuccess({ id: newNode.id });
  },
);

export const createDimensionRecord = defineAction(
  createDimensionRecordSchema,
  async ({ nodeId, dimensionTypeId, content }): Promise<ActionResult<{ id: string }>> => {
    const user = await requireAuth();

    const [node] = await db.select().from(nodes).where(eq(nodes.id, nodeId));
    if (!node) return actionError(new AppError("节点不存在", "blocking", ErrorCode.NOT_FOUND, 404));

    await checkProjectAccess(user.id, node.projectId, "editor");

    const [record] = await db
      .insert(dimensionRecords)
      .values({
        nodeId,
        dimensionTypeId,
        content,
        createdBy: user.id,
      })
      .returning();

    logger.action("dimension.create", user.id, {
      nodeId,
      dimensionTypeId,
    });
    logActivity({
      projectId: node.projectId,
      userId: user.id,
      actionType: "create",
      targetType: "dimension_record",
      targetId: record.id,
      summary: `创建维度记录`,
      metadata: { nodeId, dimensionTypeId },
    });
    revalidatePath(`/projects/${node.projectId}`);

    return actionSuccess({ id: record.id });
  },
);

export async function updateDimensionRecord(
  recordId: string,
  content: Record<string, unknown>,
  expectedVersion: number,
): Promise<ActionResult<{ id: string; version: number }>> {
  try {
    const user = await requireAuth();

    const [record] = await db
      .select()
      .from(dimensionRecords)
      .where(eq(dimensionRecords.id, recordId));

    if (!record) return actionError(new AppError("记录不存在", "blocking", "NOT_FOUND", 404));

    const [node] = await db.select().from(nodes).where(eq(nodes.id, record.nodeId));
    if (node) await checkProjectAccess(user.id, node.projectId, "editor");

    // 乐观锁检查
    if (record.version !== expectedVersion) {
      return actionError(
        new AppError("内容已被他人修改，请刷新后重试", "blocking", "VERSION_CONFLICT", 409),
      );
    }

    const [updated] = await db
      .update(dimensionRecords)
      .set({
        content,
        version: record.version + 1,
        updatedBy: user.id,
        updatedAt: new Date(),
      })
      .where(eq(dimensionRecords.id, recordId))
      .returning();

    logger.action("dimension.update", user.id, {
      recordId,
      newVersion: updated.version,
    });
    if (node)
      logActivity({
        projectId: node.projectId,
        userId: user.id,
        actionType: "update",
        targetType: "dimension_record",
        targetId: recordId,
        summary: `更新维度记录 v${updated.version}`,
        metadata: { newVersion: updated.version },
      });

    if (node) revalidatePath(`/projects/${node.projectId}`);

    return actionSuccess({ id: updated.id, version: updated.version });
  } catch (error) {
    return actionError(error);
  }
}

export async function deleteDimensionRecord(recordId: string): Promise<ActionResult> {
  try {
    const user = await requireAuth();

    const [record] = await db
      .select()
      .from(dimensionRecords)
      .where(eq(dimensionRecords.id, recordId));
    if (!record) return actionError(new AppError("记录不存在", "blocking", "NOT_FOUND", 404));

    const [node] = await db.select().from(nodes).where(eq(nodes.id, record.nodeId));
    if (node) await checkProjectAccess(user.id, node.projectId, "editor");

    await db.delete(dimensionRecords).where(eq(dimensionRecords.id, recordId));

    logger.action("dimension.delete", user.id, { recordId });
    if (node)
      logActivity({
        projectId: node.projectId,
        userId: user.id,
        actionType: "delete",
        targetType: "dimension_record",
        targetId: recordId,
        summary: `删除维度记录`,
      });

    if (node) revalidatePath(`/projects/${node.projectId}`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export const renameNode = defineAction(
  renameNodeSchema,
  async ({ nodeId, name: newName }): Promise<ActionResult> => {
    const user = await requireAuth();

    const [node] = await db.select().from(nodes).where(eq(nodes.id, nodeId));
    if (!node) return actionError(new AppError("节点不存在", "blocking", ErrorCode.NOT_FOUND, 404));

    await checkProjectAccess(user.id, node.projectId, "editor");

    await db
      .update(nodes)
      .set({ name: newName, updatedBy: user.id, updatedAt: new Date() })
      .where(eq(nodes.id, nodeId));

    logger.action("node.rename", user.id, { nodeId, newName });
    logActivity({
      projectId: node.projectId,
      userId: user.id,
      actionType: "update",
      targetType: "node",
      targetId: nodeId,
      summary: `重命名节点为 "${newName}"`,
    });
    revalidatePath(`/projects/${node.projectId}`);

    return actionSuccess(undefined);
  },
);

export const deleteNode = defineAction(
  deleteNodeSchema,
  async ({ nodeId }): Promise<ActionResult> => {
    const user = await requireAuth();

    const [node] = await db.select().from(nodes).where(eq(nodes.id, nodeId));
    if (!node) return actionError(new AppError("节点不存在", "blocking", ErrorCode.NOT_FOUND, 404));

    await checkProjectAccess(user.id, node.projectId, "editor");

    // parentId has no FK cascade — manually delete descendants first
    // Find all descendants via materialized path
    const descendants = await db
      .select({ id: nodes.id })
      .from(nodes)
      .where(and(eq(nodes.projectId, node.projectId), like(nodes.path, `%${nodeId}%`)));
    const descendantIds = descendants.map((d) => d.id);

    // Delete all descendants + the node itself in one go
    const allIds = [...descendantIds, nodeId];
    await db.delete(nodes).where(inArray(nodes.id, allIds));

    logger.action("node.delete", user.id, {
      nodeId,
      projectId: node.projectId,
    });
    logActivity({
      projectId: node.projectId,
      userId: user.id,
      actionType: "delete",
      targetType: "node",
      targetId: nodeId,
      summary: `删除节点 "${node.name}"`,
      metadata: { descendantCount: allIds.length - 1 },
    });
    revalidatePath(`/projects/${node.projectId}`);

    return actionSuccess(undefined);
  },
);

export async function getFolderOverview(nodeId: string, projectId: string) {
  const user = await requireAuth();
  await checkProjectAccess(user.id, projectId, "viewer");

  const children = await db
    .select()
    .from(nodes)
    .where(and(eq(nodes.parentId, nodeId), eq(nodes.projectId, projectId)))
    .orderBy(asc(nodes.sortOrder));

  const dimConfigs = await db
    .select()
    .from(projectDimensionConfigs)
    .where(
      and(
        eq(projectDimensionConfigs.projectId, projectId),
        eq(projectDimensionConfigs.enabled, true),
      ),
    );
  const totalDims = dimConfigs.length;

  const result = await Promise.all(
    children.map(async (child) => {
      if (child.type === "file") {
        const records = await db
          .select({ dimTypeId: dimensionRecords.dimensionTypeId })
          .from(dimensionRecords)
          .where(eq(dimensionRecords.nodeId, child.id));
        const uniqueDims = new Set(records.map((r) => r.dimTypeId));
        return {
          ...child,
          filledDimensions: uniqueDims.size,
          totalDimensions: totalDims,
          completionPercent: totalDims > 0 ? Math.round((uniqueDims.size / totalDims) * 100) : 0,
        };
      }
      const descendants = await db
        .select()
        .from(nodes)
        .where(and(eq(nodes.projectId, projectId), eq(nodes.type, "file")));
      const childDescendants = descendants.filter((d) => d.path.includes(child.id));
      return {
        ...child,
        filledDimensions: childDescendants.length,
        totalDimensions: childDescendants.length,
        completionPercent: 0,
        childCount: childDescendants.length,
      };
    }),
  );

  return result;
}

export async function getCompetitiveRecords(projectId: string) {
  const user = await requireAuth();
  await checkProjectAccess(user.id, projectId, "viewer");

  const competitiveKeys = ["competitive_ref", "competitor"];

  const records = await db
    .select({
      nodeId: nodes.id,
      nodeName: nodes.name,
      nodePath: nodes.path,
      recordId: dimensionRecords.id,
      content: dimensionRecords.content,
    })
    .from(dimensionRecords)
    .innerJoin(nodes, eq(dimensionRecords.nodeId, nodes.id))
    .innerJoin(dimensionTypes, eq(dimensionRecords.dimensionTypeId, dimensionTypes.id))
    .where(and(eq(nodes.projectId, projectId), inArray(dimensionTypes.key, competitiveKeys)));

  return records;
}

export async function getModuleRelations(projectId: string): Promise<{
  nodes: { id: string; name: string; type: string }[];
  edges: { source: string; target: string; relation: string }[];
}> {
  const user = await requireAuth();
  await checkProjectAccess(user.id, projectId, "viewer");

  // Get all nodes for this project
  const projectNodes = await db
    .select({ id: nodes.id, name: nodes.name, type: nodes.type })
    .from(nodes)
    .where(eq(nodes.projectId, projectId));

  if (projectNodes.length === 0) {
    return { nodes: [], edges: [] };
  }

  const nodeIds = projectNodes.map((n) => n.id);

  // Get relations where source or target belongs to this project
  const relations = await db
    .select({
      sourceNodeId: nodeRelations.sourceNodeId,
      targetNodeId: nodeRelations.targetNodeId,
      relationType: nodeRelations.relationType,
    })
    .from(nodeRelations)
    .where(
      or(
        inArray(nodeRelations.sourceNodeId, nodeIds),
        inArray(nodeRelations.targetNodeId, nodeIds),
      ),
    );

  // Collect all node IDs referenced in relations (may include cross-project)
  const referencedIds = new Set<string>();
  for (const rel of relations) {
    referencedIds.add(rel.sourceNodeId);
    referencedIds.add(rel.targetNodeId);
  }

  // Fetch any external nodes not already in projectNodes
  const projectNodeIds = new Set(nodeIds);
  const externalIds = [...referencedIds].filter((id) => !projectNodeIds.has(id));

  let allNodes = [...projectNodes];
  if (externalIds.length > 0) {
    const externalNodes = await db
      .select({ id: nodes.id, name: nodes.name, type: nodes.type })
      .from(nodes)
      .where(inArray(nodes.id, externalIds));
    allNodes = [...allNodes, ...externalNodes];
  }

  return {
    nodes: allNodes,
    edges: relations.map((r) => ({
      source: r.sourceNodeId,
      target: r.targetNodeId,
      relation: r.relationType,
    })),
  };
}

export async function importNodesFromCSV(
  projectId: string,
  csvContent: string,
): Promise<ActionResult<{ imported: number; errors: string[] }>> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "editor");

    // ── 解析 CSV ─────────────────────────────────────────
    const lines = csvContent.split(/\r?\n/).filter((l) => l.trim().length > 0);
    if (lines.length < 2) {
      return actionSuccess({ imported: 0, errors: ["CSV 内容为空或缺少数据行"] });
    }

    // 解析表头（支持带/不带 BOM）
    const rawHeader = lines[0].replace(/^\uFEFF/, "");
    const headers = rawHeader.split(",").map((h) => h.trim());

    const colIndex = {
      name: headers.indexOf("名称"),
      type: headers.indexOf("类型"),
      parent: headers.indexOf("父节点名称"),
      desc: headers.indexOf("描述"),
    };

    if (colIndex.name === -1) {
      return actionError(new AppError("CSV 缺少必填列：名称", "blocking", "VALIDATION_ERROR", 400));
    }

    // ── 拉取项目已有节点 ──────────────────────────────────
    const existingNodes = await db.select().from(nodes).where(eq(nodes.projectId, projectId));

    // name -> node 映射（用于父节点查找，key = parentId|name 或 root|name）
    // 使用 id 作为最终引用
    const nameToNode = new Map<string, (typeof existingNodes)[number]>();
    for (const n of existingNodes) {
      nameToNode.set(n.name, n);
    }

    // 本批次已插入的节点（name -> 临时对象），用于后续行的父节点引用
    interface PendingNode {
      id: string;
      name: string;
      parentId: string | null;
      depth: number;
      path: string;
      sortOrder: number;
      type: "folder" | "file";
    }
    const importedByName = new Map<string, PendingNode>();

    const errors: string[] = [];
    let importedCount = 0;

    // 同级名称去重：key = `${parentId ?? "root"}::${name}`
    const siblingNameSet = new Set<string>();
    for (const n of existingNodes) {
      siblingNameSet.add(`${n.parentId ?? "root"}::${n.name}`);
    }

    const dataLines = lines.slice(1);

    for (let i = 0; i < dataLines.length; i++) {
      const rowNum = i + 2; // 1-based, header is row 1
      const cols = dataLines[i].split(",").map((c) => c.trim());

      const rawName = colIndex.name >= 0 ? (cols[colIndex.name] ?? "").trim() : "";
      const rawType = colIndex.type >= 0 ? (cols[colIndex.type] ?? "").trim() : "";
      const rawParent = colIndex.parent >= 0 ? (cols[colIndex.parent] ?? "").trim() : "";

      // 名称必填
      if (!rawName) {
        errors.push(`第 ${rowNum} 行：名称为空，已跳过`);
        continue;
      }

      // 类型校验，默认 file
      let nodeType: "folder" | "file" = "file";
      if (rawType === "folder" || rawType === "文件夹") {
        nodeType = "folder";
      } else if (rawType === "file" || rawType === "文件" || rawType === "") {
        nodeType = "file";
      } else {
        errors.push(`第 ${rowNum} 行："${rawName}" 类型 "${rawType}" 无效，已按 file 处理`);
      }

      // 父节点解析
      let parentId: string | null = null;
      let depth = 0;
      let path = "";

      if (rawParent) {
        // 先找本批次已导入的，再找库中已有的
        const fromImported = importedByName.get(rawParent);
        const fromExisting = nameToNode.get(rawParent);

        if (fromImported) {
          parentId = fromImported.id;
          depth = fromImported.depth + 1;
          path = fromImported.path ? `${fromImported.path}/${fromImported.id}` : fromImported.id;
        } else if (fromExisting) {
          parentId = fromExisting.id;
          depth = fromExisting.depth + 1;
          path = fromExisting.path ? `${fromExisting.path}/${fromExisting.id}` : fromExisting.id;
        } else {
          errors.push(`第 ${rowNum} 行："${rawName}" 的父节点 "${rawParent}" 不存在，已跳过`);
          continue;
        }
      }

      // 同级名称重复检查
      const siblingKey = `${parentId ?? "root"}::${rawName}`;
      if (siblingNameSet.has(siblingKey)) {
        errors.push(`第 ${rowNum} 行："${rawName}" 在同级下已存在，已跳过`);
        continue;
      }

      // 计算 sortOrder
      const siblingsCount = [...existingNodes, ...importedByName.values()].filter(
        (n) => (n.parentId ?? null) === parentId,
      ).length;

      // 插入数据库
      const [newNode] = await db
        .insert(nodes)
        .values({
          projectId,
          parentId,
          name: rawName,
          type: nodeType,
          depth,
          sortOrder: siblingsCount,
          path,
          createdBy: user.id,
        })
        .returning();

      // 记录已导入
      importedByName.set(rawName, {
        id: newNode.id,
        name: rawName,
        parentId,
        depth,
        path,
        sortOrder: siblingsCount,
        type: nodeType,
      });
      siblingNameSet.add(siblingKey);
      // 也加入 nameToNode 以供后续行引用
      nameToNode.set(rawName, newNode);

      importedCount++;
    }

    logger.action("node.importCSV", user.id, { projectId, importedCount });
    logActivity({
      projectId,
      userId: user.id,
      actionType: "import",
      targetType: "node",
      targetId: projectId,
      summary: `CSV导入${importedCount}个节点`,
      metadata: { importedCount, errorCount: errors.length },
    });
    revalidatePath(`/projects/${projectId}`);

    return actionSuccess({ imported: importedCount, errors });
  } catch (error) {
    return actionError(error);
  }
}

export async function updateNodeSortOrder(
  nodeId: string,
  newSortOrder: number,
): Promise<ActionResult> {
  try {
    const user = await requireAuth();

    const [node] = await db.select().from(nodes).where(eq(nodes.id, nodeId));
    if (!node) return actionError(new AppError("节点不存在", "blocking", "NOT_FOUND", 404));

    await checkProjectAccess(user.id, node.projectId, "editor");

    const siblings = node.parentId
      ? await db
          .select()
          .from(nodes)
          .where(and(eq(nodes.projectId, node.projectId), eq(nodes.parentId, node.parentId!)))
      : await db
          .select()
          .from(nodes)
          .where(and(eq(nodes.projectId, node.projectId), isNull(nodes.parentId)));

    const sorted = siblings.sort((a, b) => a.sortOrder - b.sortOrder);
    const oldIndex = sorted.findIndex((s) => s.id === nodeId);
    if (oldIndex === -1)
      return actionError(new AppError("节点未找到", "blocking", "NOT_FOUND", 404));

    sorted.splice(oldIndex, 1);
    sorted.splice(newSortOrder, 0, node);

    // 事务：批量更新排序
    await db.transaction(async (tx) => {
      for (let i = 0; i < sorted.length; i++) {
        await tx.update(nodes).set({ sortOrder: i }).where(eq(nodes.id, sorted[i].id));
      }
    });

    logger.action("node.reorder", user.id, { nodeId, newSortOrder });
    revalidatePath(`/projects/${node.projectId}`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function moveNode(nodeId: string, newParentId: string | null): Promise<ActionResult> {
  try {
    const user = await requireAuth();

    const [node] = await db.select().from(nodes).where(eq(nodes.id, nodeId));
    if (!node) return actionError(new AppError("节点不存在", "blocking", "NOT_FOUND", 404));

    await checkProjectAccess(user.id, node.projectId, "editor");

    // Prevent moving to self
    if (newParentId === nodeId) {
      return actionError(
        new AppError("不能将节点移动到自身下", "blocking", "VALIDATION_ERROR", 400),
      );
    }

    // Resolve new parent
    let newParent: typeof node | null = null;
    if (newParentId) {
      const [p] = await db.select().from(nodes).where(eq(nodes.id, newParentId));
      if (!p) return actionError(new AppError("目标父节点不存在", "blocking", "NOT_FOUND", 404));
      // Prevent moving into own descendant (check if newParent's path contains nodeId)
      if (p.path.includes(nodeId)) {
        return actionError(
          new AppError("不能将节点移动到其子节点下", "blocking", "VALIDATION_ERROR", 400),
        );
      }
      newParent = p;
    }

    const newDepth = newParent ? newParent.depth + 1 : 0;
    const newPath = newParent
      ? newParent.path
        ? `${newParent.path}/${newParent.id}`
        : newParent.id
      : "";
    const depthDiff = newDepth - node.depth;
    const oldPath = node.path ? `${node.path}/${node.id}` : node.id;
    const newFullPath = newPath ? `${newPath}/${node.id}` : node.id;

    await db.transaction(async (tx) => {
      // Update the node itself
      await tx
        .update(nodes)
        .set({
          parentId: newParentId,
          depth: newDepth,
          path: newPath,
          updatedBy: user.id,
          updatedAt: new Date(),
        })
        .where(eq(nodes.id, nodeId));

      // Update all descendants: path and depth
      const descendants = await tx
        .select()
        .from(nodes)
        .where(and(eq(nodes.projectId, node.projectId), like(nodes.path, `%${nodeId}%`)));

      for (const d of descendants) {
        if (d.id === nodeId) continue;
        const updatedPath = d.path.replace(oldPath, newFullPath);
        const updatedDepth = d.depth + depthDiff;
        await tx
          .update(nodes)
          .set({ path: updatedPath, depth: updatedDepth })
          .where(eq(nodes.id, d.id));
      }
    });

    logger.action("node.move", user.id, {
      nodeId,
      newParentId,
      projectId: node.projectId,
    });
    logActivity({
      projectId: node.projectId,
      userId: user.id,
      actionType: "update",
      targetType: "node",
      targetId: nodeId,
      summary: `移动节点 "${node.name}"`,
      metadata: { newParentId },
    });
    revalidatePath(`/projects/${node.projectId}`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function getNodeDescendantCount(nodeId: string): Promise<{
  childNodeCount: number;
  dimensionRecordCount: number;
} | null> {
  const user = await requireAuth();

  const [node] = await db.select().from(nodes).where(eq(nodes.id, nodeId));
  if (!node) return null;

  await checkProjectAccess(user.id, node.projectId, "viewer");

  // Find all descendant nodes (path contains this nodeId)
  const descendants = await db
    .select({ id: nodes.id })
    .from(nodes)
    .where(and(eq(nodes.projectId, node.projectId), like(nodes.path, `%${nodeId}%`)));

  const descendantIds = descendants.map((d) => d.id).filter((id) => id !== nodeId);
  const childNodeCount = descendantIds.length;

  // Count dimension records for this node + all descendants
  const allNodeIds = [nodeId, ...descendantIds];
  const [result] = await db
    .select({ count: sql<number>`count(*)::int` })
    .from(dimensionRecords)
    .where(inArray(dimensionRecords.nodeId, allNodeIds));

  return { childNodeCount, dimensionRecordCount: result?.count ?? 0 };
}
