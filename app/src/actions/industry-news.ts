"use server";

import { revalidatePath } from "next/cache";
import {
  serverApiGet,
  serverApiPost,
  serverApiPut,
  serverApiDelete,
  UnauthenticatedError,
} from "@/lib/server-http-client";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess } from "@/lib/errors";
import { defineAction } from "@/lib/define-action";
import { createNewsSchema, updateNewsSchema, linkNewsNodeSchema } from "@/lib/validators/news";
import type { components } from "@/types/api";
import { withAuthRedirect } from "@/lib/server-action-helpers";

/**
 * M14 行业动态 server actions — design/02-modules/M14-industry-news/00-design.md §6 + §7。
 *
 * 全局豁免数据（design §9 / 06-design-principles 清单 5）：无 project_id 路径参数。
 * 后端 endpoints 已实装（api/routers/industry_news_router.py）/ 本模块只做 caller 适配。
 *
 * 与 actions/feed.ts 关系：feed.ts 是 prism v1 拷贝层 `feed_items` 工作流 stub（NOT_IMPLEMENTED）
 * 仍被 workspace.tsx / overview/page.tsx / settings/page.tsx 引用（兼容签名 / 返空数组）。
 * 本文件**不替代 feed.ts** — feed 域和 news 域不一一对应（feed 含 sources + status 流转 / news
 * 是全局共享动态 + node 关联），两者并存到子片 5 cleanup 或 feed UI 显式删除时再收敛。
 */

type NewsResponse = components["schemas"]["NewsResponse"];
type NewsListResponse = components["schemas"]["NewsListResponse"];
type NewsCreate = components["schemas"]["NewsCreate"];
type NewsUpdate = components["schemas"]["NewsUpdate"];
type NewsNodeLinkCreate = components["schemas"]["NewsNodeLinkCreate"];
type NewsNodeLinkResponse = components["schemas"]["NewsNodeLinkResponse"];

export type { NewsResponse, NewsListResponse, NewsNodeLinkResponse };

// ─── Read ──────────────────────────────────────────────────────────────────

export interface ListNewsParams {
  page?: number;
  pageSize?: number;
  tag?: string;
}

export async function listNews(params: ListNewsParams = {}): Promise<NewsListResponse> {
  return withAuthRedirect(async () => {
    const qs = new URLSearchParams();
    if (params.page !== undefined) qs.set("page", String(params.page));
    if (params.pageSize !== undefined) qs.set("page_size", String(params.pageSize));
    if (params.tag) qs.set("tag", params.tag);
    const suffix = qs.toString();
    return serverApiGet<NewsListResponse>(`/api/news${suffix ? `?${suffix}` : ""}`);
  });
}

export async function getNews(newsId: string): Promise<NewsResponse | null> {
  return withAuthRedirect(async () => {
    try {
      return await serverApiGet<NewsResponse>(`/api/news/${newsId}`);
    } catch (error) {
      if (error instanceof UnauthenticatedError) throw error;
      return null;
    }
  });
}

export async function listNewsByNode(nodeId: string): Promise<NewsListResponse> {
  return withAuthRedirect(async () => {
    return serverApiGet<NewsListResponse>(`/api/nodes/${nodeId}/news`);
  });
}

// ─── Write ─────────────────────────────────────────────────────────────────

export const createNews = defineAction(
  createNewsSchema,
  async ({
    title,
    summary,
    sourceUrl,
    publishedDate,
    tags,
  }): Promise<ActionResult<{ id: string }>> => {
    const body: NewsCreate = {
      title,
      summary: summary ?? null,
      source_url: sourceUrl ?? null,
      published_date: publishedDate ?? null,
      tags: tags ?? [],
    };
    const news = await serverApiPost<NewsResponse>(`/api/news`, body);
    logger.action("news.create", "self", { newsId: news.id });
    revalidatePath("/industry-news");
    return actionSuccess({ id: news.id });
  },
);

export const updateNews = defineAction(
  updateNewsSchema,
  async ({ newsId, title, summary, sourceUrl, publishedDate, tags }): Promise<ActionResult> => {
    // exclude_unset 范式：只把用户实际填的字段送给后端（design §7 PUT NewsUpdate exclude_unset=True 行为）
    const body: NewsUpdate = {
      ...(title !== undefined && { title }),
      ...(summary !== undefined && { summary }),
      ...(sourceUrl !== undefined && { source_url: sourceUrl }),
      ...(publishedDate !== undefined && { published_date: publishedDate }),
      ...(tags !== undefined && { tags }),
    };
    await serverApiPut<NewsResponse>(`/api/news/${newsId}`, body);
    logger.action("news.update", "self", { newsId });
    revalidatePath("/industry-news");
    return actionSuccess(undefined);
  },
);

export async function deleteNews(newsId: string): Promise<ActionResult> {
  try {
    await serverApiDelete(`/api/news/${newsId}`);
    logger.action("news.delete", "self", { newsId });
    revalidatePath("/industry-news");
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

// ─── Link / Unlink（design §8：已登录即可，与 link 对称解除）─────────────

export const linkNewsToNode = defineAction(
  linkNewsNodeSchema,
  async ({ newsId, nodeId }): Promise<ActionResult<{ nodeId: string }>> => {
    const body: NewsNodeLinkCreate = { node_id: nodeId };
    const link = await serverApiPost<NewsNodeLinkResponse>(`/api/news/${newsId}/links`, body);
    logger.action("news.link", "self", { newsId, nodeId });
    revalidatePath("/industry-news");
    return actionSuccess({ nodeId: link.node_id });
  },
);

export async function unlinkNewsFromNode(newsId: string, nodeId: string): Promise<ActionResult> {
  try {
    await serverApiDelete(`/api/news/${newsId}/links/${nodeId}`);
    logger.action("news.unlink", "self", { newsId, nodeId });
    revalidatePath("/industry-news");
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}
