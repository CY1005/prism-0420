"use server";

import { db } from "@/db";
import { nodes, nodeRelations, dimensionRecords, projectDimensionConfigs } from "@/db/schema";
import { eq, and, or, asc, sql, inArray } from "drizzle-orm";
import { revalidatePath } from "next/cache";
import { requireAuth } from "@/lib/auth";
import { checkProjectAccess } from "@/services/permission.service";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";

export async function createRelation(data: {
  sourceNodeId: string;
  targetNodeId: string;
  relationType: string;
  description?: string;
}): Promise<ActionResult<{ id: number }>> {
  try {
    const user = await requireAuth();

    // Prevent self-referencing
    if (data.sourceNodeId === data.targetNodeId) {
      return actionError(new AppError("不能创建自引用关联", "blocking", "VALIDATION_ERROR", 400));
    }

    // Validate both nodes exist
    const [sourceNode] = await db.select().from(nodes).where(eq(nodes.id, data.sourceNodeId));
    if (!sourceNode) {
      return actionError(new AppError("源节点不存在", "blocking", "NOT_FOUND", 404));
    }

    const [targetNode] = await db.select().from(nodes).where(eq(nodes.id, data.targetNodeId));
    if (!targetNode) {
      return actionError(new AppError("目标节点不存在", "blocking", "NOT_FOUND", 404));
    }

    // Check access on source node's project
    await checkProjectAccess(user.id, sourceNode.projectId, "editor");

    const [relation] = await db
      .insert(nodeRelations)
      .values({
        sourceNodeId: data.sourceNodeId,
        targetNodeId: data.targetNodeId,
        relationType: data.relationType,
        description: data.description,
        createdBy: user.id,
      })
      .returning();

    revalidatePath(`/projects/${sourceNode.projectId}`);

    return actionSuccess({ id: relation.id });
  } catch (error) {
    return actionError(error);
  }
}

export async function deleteRelation(relationId: number): Promise<ActionResult> {
  try {
    const user = await requireAuth();

    const [relation] = await db
      .select()
      .from(nodeRelations)
      .where(eq(nodeRelations.id, relationId));
    if (!relation) {
      return actionError(new AppError("关联不存在", "blocking", "NOT_FOUND", 404));
    }

    // Check access via source node
    const [sourceNode] = await db.select().from(nodes).where(eq(nodes.id, relation.sourceNodeId));
    if (sourceNode) {
      await checkProjectAccess(user.id, sourceNode.projectId, "editor");
    }

    await db.delete(nodeRelations).where(eq(nodeRelations.id, relationId));

    if (sourceNode) {
      revalidatePath(`/projects/${sourceNode.projectId}`);
    }

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function getRelationsByNode(
  nodeId: string,
): Promise<ActionResult<(typeof nodeRelations.$inferSelect)[]>> {
  try {
    const user = await requireAuth();

    const [node] = await db.select().from(nodes).where(eq(nodes.id, nodeId));
    if (!node) {
      return actionError(new AppError("节点不存在", "blocking", "NOT_FOUND", 404));
    }

    await checkProjectAccess(user.id, node.projectId, "viewer");

    const relations = await db
      .select()
      .from(nodeRelations)
      .where(or(eq(nodeRelations.sourceNodeId, nodeId), eq(nodeRelations.targetNodeId, nodeId)));

    return actionSuccess(relations);
  } catch (error) {
    return actionError(error);
  }
}

interface ModuleNode {
  id: string;
  name: string;
  featureCount: number;
  completionPercent: number;
}

interface ModuleEdge {
  sourceModuleId: string;
  targetModuleId: string;
  relationType: string;
  count: number;
}

export async function getRelationGraph(
  projectId: string,
): Promise<ActionResult<{ nodes: ModuleNode[]; edges: ModuleEdge[] }>> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "viewer");

    // Get depth=1 folders (modules)
    const modules = await db
      .select()
      .from(nodes)
      .where(and(eq(nodes.projectId, projectId), eq(nodes.type, "folder"), eq(nodes.depth, 1)))
      .orderBy(asc(nodes.sortOrder));

    if (modules.length === 0) {
      return actionSuccess({ nodes: [], edges: [] });
    }

    // Get all file nodes for feature counting and completion
    const allFiles = await db
      .select({
        id: nodes.id,
        path: nodes.path,
        parentId: nodes.parentId,
      })
      .from(nodes)
      .where(and(eq(nodes.projectId, projectId), eq(nodes.type, "file")));

    // Get enabled dimensions count
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

    // Get dimension fill counts per file
    const dimFillCounts = await db
      .select({
        nodeId: dimensionRecords.nodeId,
        filledCount: sql<number>`count(distinct ${dimensionRecords.dimensionTypeId})::int`,
      })
      .from(dimensionRecords)
      .innerJoin(nodes, eq(dimensionRecords.nodeId, nodes.id))
      .where(and(eq(nodes.projectId, projectId), eq(nodes.type, "file")))
      .groupBy(dimensionRecords.nodeId);

    const fillMap = new Map<string, number>();
    for (const r of dimFillCounts) {
      fillMap.set(r.nodeId, r.filledCount);
    }

    // Build file -> module mapping (which module does each file belong to)
    const fileToModule = new Map<string, string>();
    for (const file of allFiles) {
      for (const mod of modules) {
        if (file.path.includes(mod.id)) {
          fileToModule.set(file.id, mod.id);
          break;
        }
      }
    }

    // Build module nodes with featureCount and completion
    const moduleNodes: ModuleNode[] = modules.slice(0, 200).map((mod) => {
      const modFiles = allFiles.filter((f) => f.path.includes(mod.id));
      const featureCount = modFiles.length;

      let completionPercent = 0;
      if (featureCount > 0 && totalDims > 0) {
        const totalCompletion = modFiles.reduce((sum, f) => {
          const filled = fillMap.get(f.id) ?? 0;
          return sum + (filled / totalDims) * 100;
        }, 0);
        completionPercent = Math.round(totalCompletion / featureCount);
      }

      return {
        id: mod.id,
        name: mod.name,
        featureCount,
        completionPercent,
      };
    });

    // Get all relations in the project
    const allNodeIds = allFiles.map((f) => f.id);
    const moduleIds = modules.map((m) => m.id);
    const allProjectNodeIds = [...allNodeIds, ...moduleIds];

    let relations: { sourceNodeId: string; targetNodeId: string; relationType: string }[] = [];
    if (allProjectNodeIds.length > 0) {
      relations = await db
        .select({
          sourceNodeId: nodeRelations.sourceNodeId,
          targetNodeId: nodeRelations.targetNodeId,
          relationType: nodeRelations.relationType,
        })
        .from(nodeRelations)
        .where(
          or(
            inArray(nodeRelations.sourceNodeId, allProjectNodeIds),
            inArray(nodeRelations.targetNodeId, allProjectNodeIds),
          ),
        );
    }

    // Aggregate relations to module level
    const edgeMap = new Map<string, ModuleEdge>();
    for (const rel of relations) {
      const sourceModule = fileToModule.get(rel.sourceNodeId) ?? rel.sourceNodeId;
      const targetModule = fileToModule.get(rel.targetNodeId) ?? rel.targetNodeId;

      // Skip if same module or if either is not a known module
      const moduleIdSet = new Set(modules.map((m) => m.id));
      if (sourceModule === targetModule) continue;
      if (!moduleIdSet.has(sourceModule) || !moduleIdSet.has(targetModule)) continue;

      const key = `${sourceModule}:${targetModule}:${rel.relationType}`;
      const existing = edgeMap.get(key);
      if (existing) {
        existing.count++;
      } else {
        edgeMap.set(key, {
          sourceModuleId: sourceModule,
          targetModuleId: targetModule,
          relationType: rel.relationType,
          count: 1,
        });
      }
    }

    return actionSuccess({
      nodes: moduleNodes,
      edges: [...edgeMap.values()],
    });
  } catch (error) {
    return actionError(error);
  }
}

interface FeatureNode {
  id: string;
  name: string;
  type: string;
  completionPercent: number;
}

interface FeatureRelation {
  id: number;
  sourceNodeId: string;
  targetNodeId: string;
  relationType: string;
  description: string | null;
}

export async function getModuleRelationDetail(
  moduleNodeId: string,
): Promise<ActionResult<{ features: FeatureNode[]; relations: FeatureRelation[] }>> {
  try {
    const user = await requireAuth();

    const [moduleNode] = await db.select().from(nodes).where(eq(nodes.id, moduleNodeId));
    if (!moduleNode) {
      return actionError(new AppError("模块不存在", "blocking", "NOT_FOUND", 404));
    }

    await checkProjectAccess(user.id, moduleNode.projectId, "viewer");

    // Get child feature nodes (files directly or deeply under this module)
    const childFiles = await db
      .select()
      .from(nodes)
      .where(
        and(
          eq(nodes.projectId, moduleNode.projectId),
          eq(nodes.type, "file"),
          sql`${nodes.path} like '%' || ${moduleNodeId} || '%'`,
        ),
      );

    // Get enabled dimensions for completion
    const dimConfigs = await db
      .select()
      .from(projectDimensionConfigs)
      .where(
        and(
          eq(projectDimensionConfigs.projectId, moduleNode.projectId),
          eq(projectDimensionConfigs.enabled, true),
        ),
      );
    const totalDims = dimConfigs.length;

    // Get dimension fill counts
    const childFileIds = childFiles.map((f) => f.id);
    let fillMap = new Map<string, number>();

    if (childFileIds.length > 0) {
      const dimFillCounts = await db
        .select({
          nodeId: dimensionRecords.nodeId,
          filledCount: sql<number>`count(distinct ${dimensionRecords.dimensionTypeId})::int`,
        })
        .from(dimensionRecords)
        .where(inArray(dimensionRecords.nodeId, childFileIds))
        .groupBy(dimensionRecords.nodeId);

      for (const r of dimFillCounts) {
        fillMap.set(r.nodeId, r.filledCount);
      }
    }

    const features: FeatureNode[] = childFiles.map((f) => {
      const filled = fillMap.get(f.id) ?? 0;
      const percent = totalDims > 0 ? Math.round((filled / totalDims) * 100) : 0;
      return {
        id: f.id,
        name: f.name,
        type: f.type,
        completionPercent: percent,
      };
    });

    // Get cross-module relations: one end is inside this module, the other is outside
    let relations: FeatureRelation[] = [];
    if (childFileIds.length > 0) {
      const allRelations = await db
        .select()
        .from(nodeRelations)
        .where(
          or(
            inArray(nodeRelations.sourceNodeId, childFileIds),
            inArray(nodeRelations.targetNodeId, childFileIds),
          ),
        );

      const childFileIdSet = new Set(childFileIds);
      relations = allRelations
        .filter((r) => {
          // Cross-module: one end inside, one end outside
          const sourceInside = childFileIdSet.has(r.sourceNodeId);
          const targetInside = childFileIdSet.has(r.targetNodeId);
          return sourceInside !== targetInside;
        })
        .map((r) => ({
          id: r.id,
          sourceNodeId: r.sourceNodeId,
          targetNodeId: r.targetNodeId,
          relationType: r.relationType,
          description: r.description,
        }));
    }

    return actionSuccess({ features, relations });
  } catch (error) {
    return actionError(error);
  }
}
