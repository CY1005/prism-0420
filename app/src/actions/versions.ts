"use server";

import { revalidatePath } from "next/cache";
import { serverApiGet, serverApiPost, serverApiDelete } from "@/lib/server-http-client";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess } from "@/lib/errors";
import type { components } from "@/types/api";

type VersionResponse = components["schemas"]["VersionResponse"];
type VersionListResponse = components["schemas"]["VersionListResponse"];
type VersionCreate = components["schemas"]["VersionCreate"];

export async function getVersionsByNode(
  projectId: string,
  nodeId: string,
): Promise<VersionResponse[]> {
  try {
    const data = await serverApiGet<VersionListResponse>(
      `/api/projects/${projectId}/nodes/${nodeId}/versions`,
    );
    return data.items;
  } catch {
    return [];
  }
}

export async function createVersion(
  projectId: string,
  nodeId: string,
  versionLabel: string,
  summary: string,
  changeType: string,
  details?: string,
): Promise<ActionResult<{ id: string }>> {
  try {
    const allowed: VersionCreate["change_type"][] = [
      "added",
      "modified",
      "deprecated",
      "split",
      "merged",
      "migrated",
    ];
    const ct = (allowed as string[]).includes(changeType)
      ? (changeType as VersionCreate["change_type"])
      : "modified";

    const body: VersionCreate = {
      version_label: versionLabel,
      summary,
      details: details ?? null,
      change_type: ct,
      release_mode: "release",
      is_current: true,
    };

    const created = await serverApiPost<VersionResponse>(
      `/api/projects/${projectId}/nodes/${nodeId}/versions`,
      body,
    );

    logger.action("version.create", "self", {
      nodeId,
      versionId: created.id,
      versionLabel,
    });
    revalidatePath(`/projects/${projectId}`);

    return actionSuccess({ id: created.id });
  } catch (error) {
    return actionError(error);
  }
}

export async function getVersionSnapshot(
  projectId: string,
  nodeId: string,
  versionId: string,
): Promise<{ version: VersionResponse; snapshotData: VersionResponse["snapshot_data"] } | null> {
  try {
    const version = await serverApiGet<VersionResponse>(
      `/api/projects/${projectId}/nodes/${nodeId}/versions/${versionId}`,
    );
    return { version, snapshotData: version.snapshot_data };
  } catch {
    return null;
  }
}

export async function deleteVersion(
  projectId: string,
  nodeId: string,
  versionId: string,
): Promise<ActionResult> {
  try {
    await serverApiDelete(`/api/projects/${projectId}/nodes/${nodeId}/versions/${versionId}`);

    logger.action("version.delete", "self", { versionId, nodeId });
    revalidatePath(`/projects/${projectId}`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}
