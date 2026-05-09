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
import { defineAction } from "@/lib/define-action";
import { createCompetitorSchema } from "@/lib/validators/competitor";
import type { components } from "@/types/api";

type CompetitorResponse = components["schemas"]["CompetitorResponse"];
type CompetitorListResponse = components["schemas"]["CompetitorListResponse"];
type CompetitorCreate = components["schemas"]["CompetitorCreate"];
type CompetitorUpdate = components["schemas"]["CompetitorUpdate"];

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

export const createCompetitor = defineAction(
  createCompetitorSchema,
  async ({ projectId, name, website, description }): Promise<ActionResult<{ id: string }>> => {
    const body: CompetitorCreate = {
      display_name: name,
      website_url: website || null,
      description: description || null,
    };
    const competitor = await serverApiPost<CompetitorResponse>(
      `/api/projects/${projectId}/competitors`,
      body,
    );

    logger.action("competitor.create", "self", { projectId, competitorId: competitor.id });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess({ id: competitor.id });
  },
);

export async function updateCompetitor(
  projectId: string,
  competitorId: string,
  data: { name?: string; website?: string; description?: string },
): Promise<ActionResult> {
  try {
    if (data.name !== undefined && data.name.trim() === "") {
      return actionError(new AppError("竞品名称不能为空", "blocking", "VALIDATION_ERROR"));
    }

    const body: CompetitorUpdate = {
      ...(data.name !== undefined && { display_name: data.name.trim() }),
      ...(data.website !== undefined && { website_url: data.website.trim() || null }),
      ...(data.description !== undefined && { description: data.description.trim() || null }),
    };

    await serverApiPut<CompetitorResponse>(
      `/api/projects/${projectId}/competitors/${competitorId}`,
      body,
    );

    logger.action("competitor.update", "self", { competitorId, projectId });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function deleteCompetitor(
  projectId: string,
  competitorId: string,
): Promise<ActionResult> {
  try {
    await serverApiDelete(`/api/projects/${projectId}/competitors/${competitorId}`);

    logger.action("competitor.delete", "self", { competitorId, projectId });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function getCompetitorsByProject(projectId: string): Promise<CompetitorResponse[]> {
  return withAuthRedirect(async () => {
    const data = await serverApiGet<CompetitorListResponse>(
      `/api/projects/${projectId}/competitors`,
    );
    return data.items;
  });
}
