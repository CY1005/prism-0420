"use server";

import { db } from "@/db";
import { nodes, dimensionRecords, dimensionTypes, versionRecords } from "@/db/schema";
import { eq, and, asc, desc } from "drizzle-orm";
import { revalidatePath } from "next/cache";
import { requireAuth } from "@/lib/auth";
import { checkProjectAccess } from "@/services/permission.service";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import { logActivity } from "./activity-log";

export async function getVersionsByNode(nodeId: string) {
  const user = await requireAuth();

  const [node] = await db.select().from(nodes).where(eq(nodes.id, nodeId));
  if (!node) return [];

  await checkProjectAccess(user.id, node.projectId, "viewer");

  return db
    .select()
    .from(versionRecords)
    .where(eq(versionRecords.nodeId, nodeId))
    .orderBy(asc(versionRecords.createdAt));
}

export async function createVersion(
  nodeId: string,
  versionLabel: string,
  summary: string,
  changeType: string,
  details?: string,
): Promise<ActionResult<{ id: string }>> {
  try {
    const user = await requireAuth();

    const [node] = await db.select().from(nodes).where(eq(nodes.id, nodeId));
    if (!node) return actionError(new AppError("节点不存在", "blocking", "NOT_FOUND", 404));

    await checkProjectAccess(user.id, node.projectId, "editor");

    // Check versionLabel uniqueness per node
    const [existing] = await db
      .select({ id: versionRecords.id })
      .from(versionRecords)
      .where(and(eq(versionRecords.nodeId, nodeId), eq(versionRecords.versionLabel, versionLabel)));

    if (existing) {
      return actionError(
        new AppError(
          `版本标签 "${versionLabel}" 在该节点下已存在`,
          "blocking",
          "DUPLICATE_ENTRY",
          409,
        ),
      );
    }

    // Snapshot all dimension records for this node
    const dimRecords = await db
      .select({
        dimensionTypeId: dimensionRecords.dimensionTypeId,
        dimensionKey: dimensionTypes.key,
        dimensionName: dimensionTypes.name,
        content: dimensionRecords.content,
        version: dimensionRecords.version,
      })
      .from(dimensionRecords)
      .innerJoin(dimensionTypes, eq(dimensionRecords.dimensionTypeId, dimensionTypes.id))
      .where(eq(dimensionRecords.nodeId, nodeId));

    const snapshotData = dimRecords.map((r) => ({
      dimensionTypeId: r.dimensionTypeId,
      dimensionKey: r.dimensionKey,
      dimensionName: r.dimensionName,
      content: r.content,
      version: r.version,
    }));

    // Transaction: unset current, insert new version as current
    const [newVersion] = await db.transaction(async (tx) => {
      // Unset isCurrent on existing current version
      await tx
        .update(versionRecords)
        .set({ isCurrent: false })
        .where(and(eq(versionRecords.nodeId, nodeId), eq(versionRecords.isCurrent, true)));

      return tx
        .insert(versionRecords)
        .values({
          nodeId,
          versionLabel,
          summary,
          details: details ?? null,
          changeType,
          isCurrent: true,
          snapshotData: snapshotData as Record<string, unknown>[],
          mode: "release",
        })
        .returning();
    });

    logger.action("version.create", user.id, {
      nodeId,
      versionId: newVersion.id,
      versionLabel,
    });
    logActivity({
      projectId: node.projectId,
      userId: user.id,
      actionType: "create",
      targetType: "version",
      targetId: newVersion.id,
      summary: `创建版本 ${versionLabel}`,
      metadata: { nodeId, changeType },
    });
    revalidatePath(`/projects/${node.projectId}`);

    return actionSuccess({ id: newVersion.id });
  } catch (error) {
    return actionError(error);
  }
}

export async function getVersionSnapshot(versionId: string) {
  const user = await requireAuth();

  const [version] = await db.select().from(versionRecords).where(eq(versionRecords.id, versionId));

  if (!version) return null;

  const [node] = await db.select().from(nodes).where(eq(nodes.id, version.nodeId));
  if (!node) return null;

  await checkProjectAccess(user.id, node.projectId, "viewer");

  return {
    version,
    snapshotData: version.snapshotData,
  };
}

export async function deleteVersion(versionId: string): Promise<ActionResult> {
  try {
    const user = await requireAuth();

    const [version] = await db
      .select()
      .from(versionRecords)
      .where(eq(versionRecords.id, versionId));

    if (!version) return actionError(new AppError("版本记录不存在", "blocking", "NOT_FOUND", 404));

    const [node] = await db.select().from(nodes).where(eq(nodes.id, version.nodeId));
    if (!node) return actionError(new AppError("节点不存在", "blocking", "NOT_FOUND", 404));

    await checkProjectAccess(user.id, node.projectId, "editor");

    await db.delete(versionRecords).where(eq(versionRecords.id, versionId));

    // If deleted version was current, promote the latest remaining version
    if (version.isCurrent) {
      const [latest] = await db
        .select()
        .from(versionRecords)
        .where(eq(versionRecords.nodeId, version.nodeId))
        .orderBy(desc(versionRecords.createdAt))
        .limit(1);

      if (latest) {
        await db
          .update(versionRecords)
          .set({ isCurrent: true })
          .where(eq(versionRecords.id, latest.id));
      }
    }

    logger.action("version.delete", user.id, {
      versionId,
      nodeId: version.nodeId,
    });
    logActivity({
      projectId: node.projectId,
      userId: user.id,
      actionType: "delete",
      targetType: "version",
      targetId: versionId,
      summary: `删除版本 ${version.versionLabel}`,
      metadata: { nodeId: version.nodeId },
    });
    revalidatePath(`/projects/${node.projectId}`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}
