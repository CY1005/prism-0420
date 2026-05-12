"use server";

import { revalidatePath } from "next/cache";
import {
  serverApiGet,
  serverApiPost,
  serverApiPut,
  serverApiDelete,
} from "@/lib/server-http-client";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import { defineAction } from "@/lib/define-action";
import { createCompetitorSchema } from "@/lib/validators/competitor";
import type { components } from "@/types/api";
import { withAuthRedirect } from "@/lib/server-action-helpers";

type CompetitorResponse = components["schemas"]["CompetitorResponse"];
type CompetitorListResponse = components["schemas"]["CompetitorListResponse"];
type CompetitorCreate = components["schemas"]["CompetitorCreate"];
type CompetitorUpdate = components["schemas"]["CompetitorUpdate"];

// Phase 2.3 cleanup A: actions 层 adapter snake_case → camelCase（prism v1 component 期望）
export interface Competitor {
  id: string;
  projectId: string;
  name: string;
  website: string | null;
  description: string | null;
  createdAt: string;
}

export function toCompetitor(r: CompetitorResponse): Competitor {
  return {
    id: r.id,
    projectId: r.project_id,
    name: r.display_name,
    website: r.website_url,
    description: r.description,
    createdAt: r.created_at,
  };
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

export async function getCompetitorsByProject(projectId: string): Promise<Competitor[]> {
  return withAuthRedirect(async () => {
    const data = await serverApiGet<CompetitorListResponse>(
      `/api/projects/${projectId}/competitors`,
    );
    return data.items.map(toCompetitor);
  });
}
