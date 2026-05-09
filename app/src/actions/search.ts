"use server";

import { requireAuth } from "@/lib/auth";
import { actionError, actionSuccess, type ActionResult } from "@/lib/errors";
import { searchUnified, type SearchResponse, type SearchOptions } from "@/services/search";

export async function globalSearch(
  query: string,
  options?: {
    projectId?: string;
    dimensionType?: string;
    issueCategory?: string;
    limit?: number;
  },
): Promise<ActionResult<SearchResponse>> {
  try {
    const user = await requireAuth();

    const searchOptions: SearchOptions = {
      userId: user.id,
      projectId: options?.projectId,
      dimensionType: options?.dimensionType,
      issueCategory: options?.issueCategory,
      limit: options?.limit,
    };

    const result = await searchUnified(query, searchOptions);

    if (!result.ok) {
      return actionError(new Error(result.error));
    }

    return actionSuccess(result.data);
  } catch (error) {
    return actionError(error);
  }
}
