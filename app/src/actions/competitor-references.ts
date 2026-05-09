"use server";

import { revalidatePath } from "next/cache";
import {
  serverApiGet,
  serverApiPost,
  serverApiPut,
  serverApiDelete,
} from "@/lib/server-http-client";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess } from "@/lib/errors";
import { defineAction } from "@/lib/define-action";
import { createCompetitorReferenceSchema } from "@/lib/validators/competitor";
import type { components } from "@/types/api";
import { withAuthRedirect } from "@/lib/server-action-helpers";

type CompetitorRefResponse = components["schemas"]["CompetitorRefResponse"];
type CompetitorRefListResponse = components["schemas"]["CompetitorRefListResponse"];
type CompetitorRefCreate = components["schemas"]["CompetitorRefCreate"];
type CompetitorRefUpdate = components["schemas"]["CompetitorRefUpdate"];

export const createReference = defineAction(
  createCompetitorReferenceSchema,
  async ({
    projectId,
    nodeId,
    competitorId,
    version,
    featureCoverage,
    technicalApproach,
    prosAndCons,
  }): Promise<ActionResult<{ id: string }>> => {
    const body: CompetitorRefCreate = {
      competitor_id: competitorId,
      competitor_version: version || null,
      feature_coverage: featureCoverage || null,
      tech_approach: technicalApproach || null,
      pros_and_cons: prosAndCons ?? null,
    };
    const ref = await serverApiPost<CompetitorRefResponse>(
      `/api/projects/${projectId}/nodes/${nodeId}/competitor-refs`,
      body,
    );

    logger.action("competitor_reference.create", "self", { projectId, refId: ref.id, nodeId });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess({ id: ref.id });
  },
);

export async function updateReference(
  projectId: string,
  nodeId: string,
  referenceId: string,
  data: {
    version?: string;
    featureCoverage?: string;
    technicalApproach?: string;
    prosAndCons?: { pros: string[]; cons: string[] };
  },
): Promise<ActionResult> {
  try {
    const body: CompetitorRefUpdate = {
      ...(data.version !== undefined && { competitor_version: data.version.trim() || null }),
      ...(data.featureCoverage !== undefined && {
        feature_coverage: data.featureCoverage.trim() || null,
      }),
      ...(data.technicalApproach !== undefined && {
        tech_approach: data.technicalApproach.trim() || null,
      }),
      ...(data.prosAndCons !== undefined && { pros_and_cons: data.prosAndCons }),
    };
    await serverApiPut<CompetitorRefResponse>(
      `/api/projects/${projectId}/nodes/${nodeId}/competitor-refs/${referenceId}`,
      body,
    );

    logger.action("competitor_reference.update", "self", { referenceId, projectId });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function deleteReference(
  projectId: string,
  nodeId: string,
  referenceId: string,
): Promise<ActionResult> {
  try {
    await serverApiDelete(
      `/api/projects/${projectId}/nodes/${nodeId}/competitor-refs/${referenceId}`,
    );

    logger.action("competitor_reference.delete", "self", { referenceId, projectId });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function getReferencesByNode(
  projectId: string,
  nodeId: string,
): Promise<CompetitorRefResponse[]> {
  return withAuthRedirect(async () => {
    const data = await serverApiGet<CompetitorRefListResponse>(
      `/api/projects/${projectId}/nodes/${nodeId}/competitor-refs`,
    );
    return data.items;
  });
}
