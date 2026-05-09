"use server";

import { db } from "@/db";
import { activityLogs } from "@/db/schema";
import { eq, desc } from "drizzle-orm";
import { requireAuth } from "@/lib/auth";
import { checkProjectAccess } from "@/services/permission.service";

// ─── Log Activity (fire-and-forget, no await needed) ─────

export async function logActivity(params: {
  projectId: string;
  userId: string;
  actionType: string;
  targetType: string;
  targetId: string;
  summary: string;
  metadata?: Record<string, unknown>;
}): Promise<void> {
  try {
    await db.insert(activityLogs).values({
      projectId: params.projectId,
      userId: params.userId,
      actionType: params.actionType,
      targetType: params.targetType,
      targetId: params.targetId,
      summary: params.summary,
      metadata: params.metadata ?? null,
    });
  } catch (err) {
    // Fire-and-forget: log but don't throw to avoid affecting main flow
    console.error("Failed to log activity:", err);
  }
}

// ─── Log Activity with auto-auth (for client components) ─

export async function logActivityAuto(params: {
  projectId: string;
  actionType: string;
  targetType: string;
  targetId: string;
  summary: string;
  metadata?: Record<string, unknown>;
}): Promise<void> {
  try {
    const user = await requireAuth();
    await logActivity({ ...params, userId: user.id });
  } catch (err) {
    console.error("Failed to log activity (auto):", err);
  }
}

// ─── Get Activity Logs (paginated) ──────────────────────

export async function getActivityLogs(projectId: string, page: number = 1, pageSize: number = 20) {
  const user = await requireAuth();
  await checkProjectAccess(user.id, projectId, "viewer");

  const offset = (page - 1) * pageSize;

  const logs = await db
    .select()
    .from(activityLogs)
    .where(eq(activityLogs.projectId, projectId))
    .orderBy(desc(activityLogs.createdAt))
    .limit(pageSize)
    .offset(offset);

  return { logs, page, pageSize };
}
