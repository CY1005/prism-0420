"use server";

import { db } from "@/db";
import { projectDimensionConfigs, dimensionTypes } from "@/db/schema";
import { eq, and } from "drizzle-orm";
import { requireAuth } from "@/lib/auth";
import { checkProjectAccess } from "@/services/permission.service";
import { revalidatePath } from "next/cache";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess } from "@/lib/errors";

export type DimensionConfigRow = {
  configId: number;
  dimensionTypeId: number;
  key: string;
  name: string;
  icon: string;
  description: string | null;
  enabled: boolean;
  sortOrder: number;
};

export async function getProjectDimensionConfigs(projectId: string): Promise<DimensionConfigRow[]> {
  await requireAuth();

  const rows = await db
    .select({
      configId: projectDimensionConfigs.id,
      dimensionTypeId: projectDimensionConfigs.dimensionTypeId,
      key: dimensionTypes.key,
      name: dimensionTypes.name,
      icon: dimensionTypes.icon,
      description: dimensionTypes.description,
      enabled: projectDimensionConfigs.enabled,
      sortOrder: projectDimensionConfigs.sortOrder,
    })
    .from(projectDimensionConfigs)
    .innerJoin(dimensionTypes, eq(projectDimensionConfigs.dimensionTypeId, dimensionTypes.id))
    .where(eq(projectDimensionConfigs.projectId, projectId))
    .orderBy(projectDimensionConfigs.sortOrder);

  return rows;
}

export async function getAllDimensionTypes() {
  await requireAuth();
  return db.select().from(dimensionTypes).orderBy(dimensionTypes.id);
}

export async function updateDimensionConfig(
  projectId: string,
  configs: { dimensionTypeId: number; enabled: boolean; sortOrder: number }[],
): Promise<ActionResult> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "admin");

    await db.transaction(async (tx) => {
      for (const cfg of configs) {
        await tx
          .update(projectDimensionConfigs)
          .set({ enabled: cfg.enabled, sortOrder: cfg.sortOrder })
          .where(
            and(
              eq(projectDimensionConfigs.projectId, projectId),
              eq(projectDimensionConfigs.dimensionTypeId, cfg.dimensionTypeId),
            ),
          );
      }
    });

    logger.action("project.updateDimensionConfig", user.id, { projectId });
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}
