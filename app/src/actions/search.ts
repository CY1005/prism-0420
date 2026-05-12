"use server";

// dogfooding sprint B-list-projects-search-loader fix（2026-05-12）：
// 原 L12 `export type { SearchResponse };` 触发 Next.js 16.2.4 Turbopack
// server-actions 转换 bug — `'use server'` 文件中 `export type { X }` 命名
// 再导出说明符被 SWC 转换误识别为运行时 binding / 转译输出含 `export
// { SearchResponse }`（type 修饰符丢失）/ 服务端动作 loader 评估时抛
// `ReferenceError: SearchResponse is not defined` → /projects 页面渲染
// 0 卡片（globalSearch 模块加载失败 → projects/page/actions.js 整个动作
// 集合崩溃 → getProjects 也连带失败）。
// 修法：直接删除 dead re-export（SearchResponse 在 codebase 中无外部消费者
// / 仅作内部 globalSearch 返回类型引用 / Promise<ActionResult<SearchResponse>>
// 已自动表达 / 外部消费方靠 await 推断即可）。
// 同模式扫描（grep -n "^export type {" src/）：仅本文件命中 'use server'
// 上下文；另 2 处（issue-card / competitor-reference-card）为 'use client'
// 文件 / 不走 server actions 转换 / 安全。
// rca: _handoff/dogfooding/04-bug-fixes/B-list-projects-search-loader/rca.md
import { serverApiPost } from "@/lib/server-http-client";
import { withAuthRedirect } from "@/lib/server-action-helpers";
import { type ActionResult, actionError, actionSuccess } from "@/lib/errors";
import type { components } from "@/types/api";

type SearchRequest = components["schemas"]["SearchRequest"];
type SearchResponse = components["schemas"]["SearchResponse"];
type EmbeddingTargetType = components["schemas"]["EmbeddingTargetType"];

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
    return await withAuthRedirect(async () => {
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
    });
  } catch (error) {
    return actionError(error);
  }
}
