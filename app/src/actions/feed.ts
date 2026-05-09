"use server";

import { db } from "@/db";
import { feedItems, feedSources, feedNodeLinks, nodes } from "@/db/schema";
import { eq, and } from "drizzle-orm";
import { revalidatePath } from "next/cache";
import { requireAuth } from "@/lib/auth";
import { checkProjectAccess } from "@/services/permission.service";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";

// ─── Feed Items ──────────────────────────────────────

export async function getFeedItems(projectId: string, status: string = "pending") {
  const user = await requireAuth();
  await checkProjectAccess(user.id, projectId, "viewer");

  return db
    .select({
      id: feedItems.id,
      projectId: feedItems.projectId,
      sourceId: feedItems.sourceId,
      title: feedItems.title,
      source: feedItems.source,
      publishedDate: feedItems.publishedDate,
      summary: feedItems.summary,
      tags: feedItems.tags,
      suggestedNodeId: feedItems.suggestedNodeId,
      suggestedNodeName: nodes.name,
      confidence: feedItems.confidence,
      status: feedItems.status,
      createdAt: feedItems.createdAt,
    })
    .from(feedItems)
    .leftJoin(nodes, eq(feedItems.suggestedNodeId, nodes.id))
    .where(and(eq(feedItems.projectId, projectId), eq(feedItems.status, status)));
}

export async function confirmFeedItem(
  itemId: string,
  nodeId: string,
): Promise<ActionResult<{ id: string }>> {
  try {
    const user = await requireAuth();

    const [item] = await db.select().from(feedItems).where(eq(feedItems.id, itemId));
    if (!item) {
      return actionError(new AppError("动态条目不存在", "blocking", "NOT_FOUND", 404));
    }

    await checkProjectAccess(user.id, item.projectId, "editor");

    const [node] = await db.select().from(nodes).where(eq(nodes.id, nodeId));
    if (!node) {
      return actionError(new AppError("节点不存在", "blocking", "NOT_FOUND", 404));
    }

    // Create link
    const [link] = await db
      .insert(feedNodeLinks)
      .values({ feedItemId: itemId, nodeId })
      .returning();

    // Update status
    await db.update(feedItems).set({ status: "confirmed" }).where(eq(feedItems.id, itemId));

    logger.action("feed_item.confirm", user.id, { itemId, nodeId, projectId: item.projectId });
    revalidatePath(`/projects/${item.projectId}`);

    return actionSuccess({ id: link.id });
  } catch (error) {
    return actionError(error);
  }
}

export async function ignoreFeedItem(itemId: string): Promise<ActionResult> {
  try {
    const user = await requireAuth();

    const [item] = await db.select().from(feedItems).where(eq(feedItems.id, itemId));
    if (!item) {
      return actionError(new AppError("动态条目不存在", "blocking", "NOT_FOUND", 404));
    }

    await checkProjectAccess(user.id, item.projectId, "editor");

    await db.update(feedItems).set({ status: "ignored" }).where(eq(feedItems.id, itemId));

    logger.action("feed_item.ignore", user.id, { itemId, projectId: item.projectId });
    revalidatePath(`/projects/${item.projectId}`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function reassignFeedItem(itemId: string, nodeId: string): Promise<ActionResult> {
  try {
    const user = await requireAuth();

    const [item] = await db.select().from(feedItems).where(eq(feedItems.id, itemId));
    if (!item) {
      return actionError(new AppError("动态条目不存在", "blocking", "NOT_FOUND", 404));
    }

    await checkProjectAccess(user.id, item.projectId, "editor");

    const [node] = await db.select().from(nodes).where(eq(nodes.id, nodeId));
    if (!node) {
      return actionError(new AppError("节点不存在", "blocking", "NOT_FOUND", 404));
    }

    await db.update(feedItems).set({ suggestedNodeId: nodeId }).where(eq(feedItems.id, itemId));

    logger.action("feed_item.reassign", user.id, { itemId, nodeId, projectId: item.projectId });
    revalidatePath(`/projects/${item.projectId}`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function getFeedItemsByNode(projectId: string, nodeId: string) {
  const user = await requireAuth();
  await checkProjectAccess(user.id, projectId, "viewer");

  return db
    .select({
      id: feedItems.id,
      title: feedItems.title,
      source: feedItems.source,
      publishedDate: feedItems.publishedDate,
      summary: feedItems.summary,
      status: feedItems.status,
    })
    .from(feedNodeLinks)
    .innerJoin(feedItems, eq(feedNodeLinks.feedItemId, feedItems.id))
    .where(and(eq(feedNodeLinks.nodeId, nodeId), eq(feedItems.projectId, projectId)));
}

// ─── Feed Sources ────────────────────────────────────

export async function getFeedSources(projectId: string) {
  const user = await requireAuth();
  await checkProjectAccess(user.id, projectId, "viewer");

  return db.select().from(feedSources).where(eq(feedSources.projectId, projectId));
}

export async function createFeedSource(
  projectId: string,
  data: {
    sourceType: string;
    url: string;
    name: string;
  },
): Promise<ActionResult<{ id: string }>> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "editor");

    if (!data.name?.trim()) {
      return actionError(new AppError("名称不能为空", "blocking", "VALIDATION_ERROR"));
    }
    if (!data.url?.trim()) {
      return actionError(new AppError("URL不能为空", "blocking", "VALIDATION_ERROR"));
    }

    const [source] = await db
      .insert(feedSources)
      .values({
        projectId,
        sourceType: data.sourceType,
        url: data.url.trim(),
        name: data.name.trim(),
      })
      .returning();

    logger.action("feed_source.create", user.id, { projectId, sourceId: source.id });
    revalidatePath(`/projects/${projectId}`);

    return actionSuccess({ id: source.id });
  } catch (error) {
    return actionError(error);
  }
}

export async function updateFeedSource(
  sourceId: string,
  data: {
    name?: string;
    url?: string;
    isActive?: boolean;
  },
): Promise<ActionResult> {
  try {
    const user = await requireAuth();

    const [source] = await db.select().from(feedSources).where(eq(feedSources.id, sourceId));
    if (!source) {
      return actionError(new AppError("订阅源不存在", "blocking", "NOT_FOUND", 404));
    }

    await checkProjectAccess(user.id, source.projectId, "editor");

    await db
      .update(feedSources)
      .set({
        ...(data.name !== undefined && { name: data.name.trim() }),
        ...(data.url !== undefined && { url: data.url.trim() }),
        ...(data.isActive !== undefined && { isActive: data.isActive }),
      })
      .where(eq(feedSources.id, sourceId));

    logger.action("feed_source.update", user.id, { sourceId, projectId: source.projectId });
    revalidatePath(`/projects/${source.projectId}`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function deleteFeedSource(sourceId: string): Promise<ActionResult> {
  try {
    const user = await requireAuth();

    const [source] = await db.select().from(feedSources).where(eq(feedSources.id, sourceId));
    if (!source) {
      return actionError(new AppError("订阅源不存在", "blocking", "NOT_FOUND", 404));
    }

    await checkProjectAccess(user.id, source.projectId, "editor");

    await db.delete(feedSources).where(eq(feedSources.id, sourceId));

    logger.action("feed_source.delete", user.id, { sourceId, projectId: source.projectId });
    revalidatePath(`/projects/${source.projectId}`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}
