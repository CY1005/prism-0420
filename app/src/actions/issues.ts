"use server";

import { db } from "@/db";
import { issues, nodes } from "@/db/schema";
import { eq, and } from "drizzle-orm";
import { revalidatePath } from "next/cache";
import { requireAuth } from "@/lib/auth";
import { checkProjectAccess } from "@/services/permission.service";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import { ErrorCode } from "@/lib/error-codes";
import { defineAction } from "@/lib/define-action";
import { createIssueSchema, updateIssueSchema, ISSUE_CATEGORIES } from "@/lib/validators/issue";

type IssueCategory = (typeof ISSUE_CATEGORIES)[number];

// ADR-012: 问题按分类自动关联到对应维度
const CATEGORY_DIMENSION_MAP: Record<IssueCategory, string> = {
  bug: "test_analysis",
  tech_debt: "engineering_exp",
  design_flaw: "design_decision",
  performance: "tech_impl",
};

export const createIssue = defineAction(
  createIssueSchema,
  async ({
    projectId,
    nodeId,
    category,
    description,
    tags,
  }): Promise<ActionResult<{ id: string }>> => {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "editor");

    if (nodeId) {
      const [node] = await db.select().from(nodes).where(eq(nodes.id, nodeId));
      if (!node || node.projectId !== projectId) {
        return actionError(
          new AppError("节点不存在或不属于该项目", "blocking", ErrorCode.NOT_FOUND, 404),
        );
      }
    }

    const [issue] = await db
      .insert(issues)
      .values({
        projectId,
        nodeId,
        category,
        description,
        tags: tags || [],
      })
      .returning();

    logger.action("issue.create", user.id, { projectId, issueId: issue.id, category });
    revalidatePath(`/projects/${projectId}`);

    return actionSuccess({ id: issue.id });
  },
);

export const updateIssue = defineAction(
  updateIssueSchema,
  async ({ issueId, category, description, tags }): Promise<ActionResult> => {
    const user = await requireAuth();

    const [issue] = await db.select().from(issues).where(eq(issues.id, issueId));
    if (!issue) {
      return actionError(new AppError("问题不存在", "blocking", ErrorCode.NOT_FOUND, 404));
    }

    await checkProjectAccess(user.id, issue.projectId, "editor");

    await db
      .update(issues)
      .set({
        ...(category !== undefined && { category }),
        ...(description !== undefined && { description }),
        ...(tags !== undefined && { tags }),
        updatedAt: new Date(),
      })
      .where(eq(issues.id, issueId));

    logger.action("issue.update", user.id, { issueId, projectId: issue.projectId });
    revalidatePath(`/projects/${issue.projectId}`);

    return actionSuccess(undefined);
  },
);

export async function deleteIssue(issueId: string): Promise<ActionResult> {
  try {
    const user = await requireAuth();

    const [issue] = await db.select().from(issues).where(eq(issues.id, issueId));
    if (!issue) {
      return actionError(new AppError("问题不存在", "blocking", "NOT_FOUND", 404));
    }

    await checkProjectAccess(user.id, issue.projectId, "editor");

    await db.delete(issues).where(eq(issues.id, issueId));

    logger.action("issue.delete", user.id, { issueId, projectId: issue.projectId });
    revalidatePath(`/projects/${issue.projectId}`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function getIssuesByNode(projectId: string, nodeId: string) {
  const user = await requireAuth();
  await checkProjectAccess(user.id, projectId, "viewer");

  return db
    .select()
    .from(issues)
    .where(and(eq(issues.projectId, projectId), eq(issues.nodeId, nodeId)));
}

export async function getIssuesByCategory(projectId: string, category: string) {
  const user = await requireAuth();
  await checkProjectAccess(user.id, projectId, "viewer");

  if (!ISSUE_CATEGORIES.includes(category as IssueCategory)) {
    return [];
  }

  return db
    .select()
    .from(issues)
    .where(and(eq(issues.projectId, projectId), eq(issues.category, category)));
}
