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

// Phase 2.3 cleanup A: actions 层组装 nested + camelCase form（prism v1 component 期望）
import { type Competitor, getCompetitorsByProject } from "@/actions/competitors";

export interface CompetitorReference {
  reference: {
    id: string;
    nodeId: string;
    competitorId: string;
    version: string | null;
    featureCoverage: string | null;
    technicalApproach: string | null;
    prosAndCons: { pros: string[]; cons: string[] } | null;
    createdAt: string;
    updatedAt: string;
  };
  competitor: Competitor;
}

function toCompetitorReference(
  r: CompetitorRefResponse,
  competitorById: Map<string, Competitor>,
): CompetitorReference | null {
  const competitor = competitorById.get(r.competitor_id);
  if (!competitor) return null;
  const pac = r.pros_and_cons as { pros?: unknown; cons?: unknown } | null;
  const prosAndCons =
    pac && Array.isArray(pac.pros) && Array.isArray(pac.cons)
      ? {
          pros: pac.pros.filter((p): p is string => typeof p === "string"),
          cons: pac.cons.filter((c): c is string => typeof c === "string"),
        }
      : null;
  return {
    reference: {
      id: r.id,
      nodeId: r.node_id,
      competitorId: r.competitor_id,
      version: r.competitor_version,
      featureCoverage: r.feature_coverage,
      technicalApproach: r.tech_approach,
      prosAndCons,
      createdAt: r.created_at,
      updatedAt: r.updated_at,
    },
    competitor,
  };
}

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

export async function updateCompetitorReference(
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

export async function deleteCompetitorReference(
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

export async function listCompetitorReferencesByNode(
  projectId: string,
  nodeId: string,
): Promise<CompetitorReference[]> {
  return withAuthRedirect(async () => {
    const [data, competitors] = await Promise.all([
      serverApiGet<CompetitorRefListResponse>(
        `/api/projects/${projectId}/nodes/${nodeId}/competitor-refs`,
      ),
      getCompetitorsByProject(projectId),
    ]);
    const competitorById = new Map(competitors.map((c) => [c.id, c]));
    return data.items
      .map((r) => toCompetitorReference(r, competitorById))
      .filter((x): x is CompetitorReference => x !== null);
  });
}
