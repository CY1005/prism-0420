"use server";

import { serverApiGet } from "@/lib/server-http-client";
import { type ActionResult, actionError, actionSuccess } from "@/lib/errors";
import type { components } from "@/types/api";
import { withAuthRedirect } from "@/lib/server-action-helpers";
import { findInTree } from "@/lib/tree-utils";

type OverviewResponse = components["schemas"]["OverviewResponse"];
type OverviewStatsResponse = components["schemas"]["OverviewStatsResponse"];
type NodeOverview = components["schemas"]["NodeOverview"];

interface TreemapItem {
  nodeId: string;
  name: string;
  type: string;
  featureCount: number;
  completionPercent: number;
}

/**
 * Treemap 数据（拷贝层 treemap-view 消费）。
 * 后端 /overview 端点已返 NodeOverview 树（含 completion_rate）。
 * 此处取根 / 给定 parentId 的直接子节点 + 派生 featureCount（folder = leaf file 数 / file = 1）。
 */
export async function getPanoramaData(
  projectId: string,
  parentId?: string,
): Promise<ActionResult<TreemapItem[]>> {
  try {
    return await withAuthRedirect(async () => {
      const overview = await serverApiGet<OverviewResponse>(`/api/projects/${projectId}/overview`);

      const children: NodeOverview[] = parentId
        ? (findInTree(overview.tree, parentId)?.children ?? [])
        : overview.tree;

      const items: TreemapItem[] = children.map((child) => {
        if (child.type === "file") {
          return {
            nodeId: child.id,
            name: child.name,
            type: child.type,
            featureCount: 1,
            completionPercent: Math.round(child.completion_rate * 100),
          };
        }
        // folder：递归统计 leaf file 数 + 平均完善度
        let fileCount = 0;
        let completionSum = 0;
        const walk = (n: NodeOverview) => {
          if (n.type === "file") {
            fileCount++;
            completionSum += n.completion_rate;
          }
          n.children.forEach(walk);
        };
        walk(child);
        return {
          nodeId: child.id,
          name: child.name,
          type: child.type,
          featureCount: fileCount,
          completionPercent: fileCount > 0 ? Math.round((completionSum / fileCount) * 100) : 0,
        };
      });

      return actionSuccess(items);
    });
  } catch (error) {
    return actionError(error);
  }
}

interface ProjectStatsResult {
  totalModules: number;
  totalFeatures: number;
  avgCompletion: number;
  lastUpdatedAt: Date | null;
}

/**
 * 项目统计（M16 stats / overview/stats 端点）。
 * 后端 OverviewStats 字段映射：
 *  - file_nodes → totalFeatures
 *  - total_nodes - file_nodes → totalModules（folder 数）
 *  - avg_completion_rate (0-1) → avgCompletion (0-100)
 *  - lastUpdatedAt：后端 stats 不返时间 / 此处保留 null（拷贝层 UI 拿不到 → 不显示）
 */
export async function getProjectStats(
  projectId: string,
): Promise<ActionResult<ProjectStatsResult>> {
  try {
    return await withAuthRedirect(async () => {
      const data = await serverApiGet<OverviewStatsResponse>(
        `/api/projects/${projectId}/overview/stats`,
      );
      const totalNodes = data.stats.total_nodes;
      const fileNodes = data.stats.file_nodes;
      return actionSuccess({
        totalModules: Math.max(0, totalNodes - fileNodes),
        totalFeatures: fileNodes,
        avgCompletion: Math.round(data.stats.avg_completion_rate * 100),
        lastUpdatedAt: null,
      });
    });
  } catch (error) {
    return actionError(error);
  }
}
