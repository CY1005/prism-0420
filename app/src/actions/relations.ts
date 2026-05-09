"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  serverApiGet,
  serverApiPost,
  serverApiDelete,
  UnauthenticatedError,
} from "@/lib/server-http-client";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import type { components } from "@/types/api";

type RelationResponse = components["schemas"]["RelationResponse"];
type RelationListResponse = components["schemas"]["RelationListResponse"];
type OverviewResponse = components["schemas"]["OverviewResponse"];
type NodeOverview = components["schemas"]["NodeOverview"];

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

interface RelationCreatePayload {
  source_node_id: string;
  target_node_id: string;
  relation_type: string;
  notes?: string | null;
}

/**
 * 创建节点关系（M08）— 后端字段：source/target/relation_type/notes（前端兼容旧 description → 映射到 notes）。
 */
export async function createRelation(data: {
  sourceNodeId: string;
  targetNodeId: string;
  relationType: string;
  description?: string;
  projectId: string;
}): Promise<ActionResult<{ id: string }>> {
  try {
    if (data.sourceNodeId === data.targetNodeId) {
      return actionError(new AppError("不能创建自引用关联", "blocking", "VALIDATION_ERROR", 400));
    }
    const body: RelationCreatePayload = {
      source_node_id: data.sourceNodeId,
      target_node_id: data.targetNodeId,
      relation_type: data.relationType,
      notes: data.description ?? null,
    };
    const relation = await serverApiPost<RelationResponse>(
      `/api/projects/${data.projectId}/relations`,
      body,
    );
    revalidatePath(`/projects/${data.projectId}`);
    return actionSuccess({ id: relation.id });
  } catch (error) {
    return actionError(error);
  }
}

export async function deleteRelation(relationId: string, projectId: string): Promise<ActionResult> {
  try {
    await serverApiDelete(`/api/projects/${projectId}/relations/${relationId}`);
    revalidatePath(`/projects/${projectId}`);
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function getRelationsByNode(
  nodeId: string,
  projectId: string,
): Promise<ActionResult<RelationResponse[]>> {
  try {
    return await withAuthRedirect(async () => {
      const data = await serverApiGet<RelationListResponse>(
        `/api/projects/${projectId}/nodes/${nodeId}/relations`,
      );
      return actionSuccess(data.items);
    });
  } catch (error) {
    return actionError(error);
  }
}

interface ModuleNode {
  id: string;
  name: string;
  featureCount: number;
  completionPercent: number;
}

interface ModuleEdge {
  sourceModuleId: string;
  targetModuleId: string;
  relationType: string;
  count: number;
}

/**
 * 模块级关系图（拷贝层 relation-graph 消费）。
 * 后端 /relations 仅返原子关系 / 此处前端聚合：
 *  1. 取 /overview → modules = depth=1 folder + 完善度
 *  2. 取 /relations → 全量原子 / file → owning module 映射后聚合 (source, target, relation_type) 计数
 */
export async function getRelationGraph(
  projectId: string,
): Promise<ActionResult<{ nodes: ModuleNode[]; edges: ModuleEdge[] }>> {
  try {
    return await withAuthRedirect(async () => {
      const overview = await serverApiGet<OverviewResponse>(`/api/projects/${projectId}/overview`);
      const relations = await serverApiGet<RelationListResponse>(
        `/api/projects/${projectId}/relations`,
      );

      // depth=1 folders
      const modules: NodeOverview[] = [];
      for (const root of overview.tree) {
        for (const child of root.children) {
          if (child.type === "folder") modules.push(child);
        }
      }
      // 兼容旧实装：若 root level 自身就是 depth=1 folder，也认作 module
      for (const root of overview.tree) {
        if (root.type === "folder" && root.depth === 1) modules.push(root);
      }

      const moduleNodes: ModuleNode[] = modules.slice(0, 200).map((mod) => {
        const featureFiles: NodeOverview[] = [];
        const walk = (n: NodeOverview) => {
          if (n.type === "file") featureFiles.push(n);
          n.children.forEach(walk);
        };
        mod.children.forEach(walk);
        const featureCount = featureFiles.length;
        const completionPercent =
          featureCount > 0
            ? Math.round(
                (featureFiles.reduce((s, f) => s + f.completion_rate, 0) / featureCount) * 100,
              )
            : 0;
        return { id: mod.id, name: mod.name, featureCount, completionPercent };
      });

      // file → owning module 映射（path 前缀 / fallback 用 path includes mod.id）
      const fileToModule = new Map<string, string>();
      const allFiles: { id: string }[] = [];
      const collectFiles = (n: NodeOverview) => {
        if (n.type === "file") allFiles.push({ id: n.id });
        n.children.forEach(collectFiles);
      };
      overview.tree.forEach(collectFiles);

      for (const mod of modules) {
        const walk = (n: NodeOverview) => {
          if (n.type === "file") fileToModule.set(n.id, mod.id);
          n.children.forEach(walk);
        };
        mod.children.forEach(walk);
      }

      const moduleIdSet = new Set(modules.map((m) => m.id));
      const edgeMap = new Map<string, ModuleEdge>();
      for (const rel of relations.items) {
        const sourceModule = fileToModule.get(rel.source_node_id) ?? rel.source_node_id;
        const targetModule = fileToModule.get(rel.target_node_id) ?? rel.target_node_id;
        if (sourceModule === targetModule) continue;
        if (!moduleIdSet.has(sourceModule) || !moduleIdSet.has(targetModule)) continue;
        const key = `${sourceModule}:${targetModule}:${rel.relation_type}`;
        const existing = edgeMap.get(key);
        if (existing) existing.count++;
        else
          edgeMap.set(key, {
            sourceModuleId: sourceModule,
            targetModuleId: targetModule,
            relationType: rel.relation_type,
            count: 1,
          });
      }

      return actionSuccess({ nodes: moduleNodes, edges: [...edgeMap.values()] });
    });
  } catch (error) {
    return actionError(error);
  }
}

interface FeatureNode {
  id: string;
  name: string;
  type: string;
  completionPercent: number;
}

interface FeatureRelation {
  id: string;
  sourceNodeId: string;
  targetNodeId: string;
  relationType: string;
  description: string | null;
}

/**
 * 模块详情（拷贝层 relation-graph 钻取消费）。
 * 后端无聚合端点 / 前端从 /overview + /relations 派生。
 */
export async function getModuleRelationDetail(
  moduleNodeId: string,
  projectId: string,
): Promise<ActionResult<{ features: FeatureNode[]; relations: FeatureRelation[] }>> {
  try {
    return await withAuthRedirect(async () => {
      const overview = await serverApiGet<OverviewResponse>(`/api/projects/${projectId}/overview`);
      const findInTree = (tree: NodeOverview[], id: string): NodeOverview | null => {
        for (const n of tree) {
          if (n.id === id) return n;
          const sub = findInTree(n.children, id);
          if (sub) return sub;
        }
        return null;
      };
      const moduleNode = findInTree(overview.tree, moduleNodeId);
      if (!moduleNode) {
        return actionError(new AppError("模块不存在", "blocking", "NOT_FOUND", 404));
      }

      const childFiles: NodeOverview[] = [];
      const walk = (n: NodeOverview) => {
        if (n.type === "file") childFiles.push(n);
        n.children.forEach(walk);
      };
      moduleNode.children.forEach(walk);

      const features: FeatureNode[] = childFiles.map((f) => ({
        id: f.id,
        name: f.name,
        type: f.type,
        completionPercent: Math.round(f.completion_rate * 100),
      }));

      const childFileIdSet = new Set(childFiles.map((f) => f.id));
      const relations = await serverApiGet<RelationListResponse>(
        `/api/projects/${projectId}/relations`,
      );

      const crossModule = relations.items
        .filter((r) => {
          const inSrc = childFileIdSet.has(r.source_node_id);
          const inTgt = childFileIdSet.has(r.target_node_id);
          return inSrc !== inTgt;
        })
        .map<FeatureRelation>((r) => ({
          id: r.id,
          sourceNodeId: r.source_node_id,
          targetNodeId: r.target_node_id,
          relationType: r.relation_type,
          description: r.notes,
        }));

      return actionSuccess({ features, relations: crossModule });
    });
  } catch (error) {
    return actionError(error);
  }
}
