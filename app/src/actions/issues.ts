"use server";

import { revalidatePath } from "next/cache";
import {
  serverApiGet,
  serverApiPost,
  serverApiPut,
  serverApiDelete,
  UnauthenticatedError,
} from "@/lib/server-http-client";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess } from "@/lib/errors";
import { defineAction } from "@/lib/define-action";
import { createIssueSchema, updateIssueSchema, ISSUE_CATEGORIES } from "@/lib/validators/issue";
import type { components } from "@/types/api";
import { withAuthRedirect } from "@/lib/server-action-helpers";

type IssueResponse = components["schemas"]["IssueResponse"];
type IssueListResponse = components["schemas"]["IssueListResponse"];
type IssueCreate = components["schemas"]["IssueCreate"];
type IssueUpdate = components["schemas"]["IssueUpdate"];
type IssueTransition = components["schemas"]["IssueTransition"];

type IssueCategory = (typeof ISSUE_CATEGORIES)[number];

export const createIssue = defineAction(
  createIssueSchema,
  async ({
    projectId,
    nodeId,
    category,
    title,
    description,
    tags,
    assignedTo,
  }): Promise<ActionResult<{ id: string }>> => {
    const body: IssueCreate = {
      node_id: nodeId,
      category,
      title,
      description,
      tags: tags ?? [],
      assigned_to: assignedTo ?? null,
    };
    const issue = await serverApiPost<IssueResponse>(`/api/projects/${projectId}/issues`, body);

    logger.action("issue.create", "self", { projectId, issueId: issue.id, category });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess({ id: issue.id });
  },
);

export const updateIssue = defineAction(
  updateIssueSchema,
  async ({
    issueId,
    projectId,
    title,
    description,
    tags,
    nodeId,
    assignedTo,
  }): Promise<ActionResult> => {
    const body: IssueUpdate = {
      ...(title !== undefined && { title }),
      ...(description !== undefined && { description }),
      ...(tags !== undefined && { tags }),
      ...(nodeId !== undefined && { node_id: nodeId }),
      ...(assignedTo !== undefined && { assigned_to: assignedTo }),
    };
    await serverApiPut<IssueResponse>(`/api/projects/${projectId}/issues/${issueId}`, body);

    logger.action("issue.update", "self", { issueId, projectId });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess(undefined);
  },
);

export async function deleteIssue(projectId: string, issueId: string): Promise<ActionResult> {
  try {
    await serverApiDelete(`/api/projects/${projectId}/issues/${issueId}`);

    logger.action("issue.delete", "self", { issueId, projectId });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function transitionIssue(
  projectId: string,
  issueId: string,
  payload: IssueTransition,
): Promise<ActionResult<IssueResponse>> {
  try {
    const issue = await serverApiPost<IssueResponse>(
      `/api/projects/${projectId}/issues/${issueId}/transition`,
      payload,
    );
    logger.action("issue.transition", "self", {
      issueId,
      projectId,
      target: payload.target_status,
    });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess(issue);
  } catch (error) {
    return actionError(error);
  }
}

export async function getIssue(projectId: string, issueId: string): Promise<IssueResponse | null> {
  return withAuthRedirect(async () => {
    try {
      return await serverApiGet<IssueResponse>(`/api/projects/${projectId}/issues/${issueId}`);
    } catch (error) {
      if (error instanceof UnauthenticatedError) throw error;
      return null;
    }
  });
}

export async function listIssues(
  projectId: string,
  filter?: {
    category?: IssueCategory;
    status?: string;
    nodeId?: string;
    tag?: string;
    limit?: number;
  },
): Promise<IssueResponse[]> {
  return withAuthRedirect(async () => {
    const params = new URLSearchParams();
    if (filter?.category) params.set("category", filter.category);
    if (filter?.status) params.set("status", filter.status);
    if (filter?.nodeId) params.set("node_id", filter.nodeId);
    if (filter?.tag) params.set("tag", filter.tag);
    if (filter?.limit !== undefined) params.set("limit", String(filter.limit));
    const qs = params.toString();
    const data = await serverApiGet<IssueListResponse>(
      `/api/projects/${projectId}/issues${qs ? `?${qs}` : ""}`,
    );
    return data.items;
  });
}

export async function listIssuesByNode(
  projectId: string,
  nodeId: string,
): Promise<IssueResponse[]> {
  return withAuthRedirect(async () => {
    const data = await serverApiGet<IssueListResponse>(
      `/api/projects/${projectId}/nodes/${nodeId}/issues`,
    );
    return data.items;
  });
}

export async function listIssuesByCategory(
  projectId: string,
  category: string,
): Promise<IssueResponse[]> {
  if (!ISSUE_CATEGORIES.includes(category as IssueCategory)) {
    return [];
  }
  return listIssues(projectId, { category: category as IssueCategory });
}
