"use server";

import { serverApiPost, UnauthenticatedError } from "@/lib/server-http-client";
import { redirect } from "next/navigation";
import { type ActionResult, actionError, actionSuccess } from "@/lib/errors";
import type { components } from "@/types/api";

type SearchRequest = components["schemas"]["SearchRequest"];
type SearchResponse = components["schemas"]["SearchResponse"];
type EmbeddingTargetType = components["schemas"]["EmbeddingTargetType"];

export type { SearchResponse };

export async function globalSearch(
  query: string,
  options?: {
    projectId?: string;
    targetTypes?: EmbeddingTargetType[];
    limit?: number;
  },
): Promise<ActionResult<SearchResponse>> {
  if (!options?.projectId) {
    return actionError(
      new Error("projectId 必填（prism-0420 search 接 /api/projects/{pid}/search）"),
    );
  }

  try {
    const body: SearchRequest = {
      query,
      target_types: options.targetTypes ?? null,
      limit: options.limit ?? 20,
    };
    const data = await serverApiPost<SearchResponse>(
      `/api/projects/${options.projectId}/search`,
      body,
    );
    return actionSuccess(data);
  } catch (error) {
    if (error instanceof UnauthenticatedError) {
      redirect("/login");
    }
    return actionError(error);
  }
}
