"use server";

import { revalidatePath } from "next/cache";
import { serverApiGet, serverApiPut } from "@/lib/server-http-client";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess } from "@/lib/errors";
import type { components } from "@/types/api";

type DimensionConfigListResponse = components["schemas"]["DimensionConfigListResponse"];
type DimensionConfigBatchUpdate = components["schemas"]["DimensionConfigBatchUpdate"];

export type DimensionConfigRow = {
  configId: number;
  dimensionTypeId: number;
  key: string;
  name: string;
  icon: string | null;
  description: string | null;
  enabled: boolean;
  sortOrder: number;
};

export async function getProjectDimensionConfigs(projectId: string): Promise<DimensionConfigRow[]> {
  const data = await serverApiGet<DimensionConfigListResponse>(
    `/api/projects/${projectId}/dimension-configs`,
  );
  return data.items.map((item) => ({
    configId: item.id,
    dimensionTypeId: item.dimension_type_id,
    key: item.dimension_type_key,
    name: item.dimension_type_name,
    icon: null,
    description: null,
    enabled: item.enabled,
    sortOrder: item.sort_order,
  }));
}

/**
 * P2 punt：后端无 /api/dimension-types 全局列表 endpoint（仅 nested DimensionTypeRef）/
 * 目前返回空数组让 UI 退化为「仅已配置维度」视图。
 * → 子片 5 / cross-sprint pool 评估是否补 endpoint。
 */
export async function getAllDimensionTypes(): Promise<DimensionConfigRow[]> {
  return [];
}

export async function updateDimensionConfig(
  projectId: string,
  configs: { dimensionTypeId: number; enabled: boolean; sortOrder: number }[],
): Promise<ActionResult> {
  try {
    const body: DimensionConfigBatchUpdate = {
      configs: configs.map((c) => ({
        dimension_type_id: c.dimensionTypeId,
        enabled: c.enabled,
        sort_order: c.sortOrder,
      })),
    };
    await serverApiPut(`/api/projects/${projectId}/dimension-configs`, body);

    logger.action("project.updateDimensionConfig", "self", { projectId });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}
