"use server";

import { db } from "@/db";
import { nodes, dimensionRecords, projectDimensionConfigs } from "@/db/schema";
import { eq, and, asc, sql, isNull, max } from "drizzle-orm";
import { requireAuth } from "@/lib/auth";
import { checkProjectAccess } from "@/services/permission.service";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";

interface TreemapItem {
  nodeId: string;
  name: string;
  type: string;
  featureCount: number;
  completionPercent: number;
}

export async function getPanoramaData(
  projectId: string,
  parentId?: string,
): Promise<ActionResult<TreemapItem[]>> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "viewer");

    // Get children of parentId (or root nodes if no parentId)
    const children = parentId
      ? await db
          .select()
          .from(nodes)
          .where(and(eq(nodes.projectId, projectId), eq(nodes.parentId, parentId)))
          .orderBy(asc(nodes.sortOrder))
      : await db
          .select()
          .from(nodes)
          .where(and(eq(nodes.projectId, projectId), isNull(nodes.parentId)))
          .orderBy(asc(nodes.sortOrder));

    // Get enabled dimension count for completion calculation
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

    // Get all file nodes in the project for counting descendants
    const allFileNodes = await db
      .select({
        id: nodes.id,
        path: nodes.path,
        parentId: nodes.parentId,
      })
      .from(nodes)
      .where(and(eq(nodes.projectId, projectId), eq(nodes.type, "file")));

    // Get dimension fill counts per file node
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

    const items: TreemapItem[] = children.map((child) => {
      if (child.type === "file") {
        const filled = fillMap.get(child.id) ?? 0;
        const percent = totalDims > 0 ? Math.round((filled / totalDims) * 100) : 0;
        return {
          nodeId: child.id,
          name: child.name,
          type: child.type,
          featureCount: 1,
          completionPercent: percent,
        };
      }

      // Folder: count leaf file nodes under it (path contains child.id)
      const descendantFiles = allFileNodes.filter((f) => f.path.includes(child.id));
      const featureCount = descendantFiles.length;

      // Average completion of descendant files
      let avgCompletion = 0;
      if (featureCount > 0 && totalDims > 0) {
        const totalCompletion = descendantFiles.reduce((sum, f) => {
          const filled = fillMap.get(f.id) ?? 0;
          return sum + (filled / totalDims) * 100;
        }, 0);
        avgCompletion = Math.round(totalCompletion / featureCount);
      }

      return {
        nodeId: child.id,
        name: child.name,
        type: child.type,
        featureCount,
        completionPercent: avgCompletion,
      };
    });

    return actionSuccess(items);
  } catch (error) {
    return actionError(error);
  }
}

interface ProjectStatsResult {
  totalModules: number;
  totalFeatures: number;
  avgCompletion: number;
  lastUpdatedAt: Date | null;
}

export async function getProjectStats(
  projectId: string,
): Promise<ActionResult<ProjectStatsResult>> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "viewer");

    // Count folders and files
    const [counts] = await db
      .select({
        totalModules: sql<number>`count(*) filter (where ${nodes.type} = 'folder')::int`,
        totalFeatures: sql<number>`count(*) filter (where ${nodes.type} = 'file')::int`,
        lastUpdatedAt: max(nodes.updatedAt),
      })
      .from(nodes)
      .where(eq(nodes.projectId, projectId));

    const totalModules = counts?.totalModules ?? 0;
    const totalFeatures = counts?.totalFeatures ?? 0;
    const lastUpdatedAt = counts?.lastUpdatedAt ?? null;

    // Calculate average completion across all file nodes
    let avgCompletion = 0;
    if (totalFeatures > 0) {
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

      if (totalDims > 0) {
        const dimFillCounts = await db
          .select({
            nodeId: dimensionRecords.nodeId,
            filledCount: sql<number>`count(distinct ${dimensionRecords.dimensionTypeId})::int`,
          })
          .from(dimensionRecords)
          .innerJoin(nodes, eq(dimensionRecords.nodeId, nodes.id))
          .where(and(eq(nodes.projectId, projectId), eq(nodes.type, "file")))
          .groupBy(dimensionRecords.nodeId);

        const totalCompletion = dimFillCounts.reduce((sum, r) => {
          return sum + (r.filledCount / totalDims) * 100;
        }, 0);
        avgCompletion = Math.round(totalCompletion / totalFeatures);
      }
    }

    return actionSuccess({
      totalModules,
      totalFeatures,
      avgCompletion,
      lastUpdatedAt,
    });
  } catch (error) {
    return actionError(error);
  }
}
