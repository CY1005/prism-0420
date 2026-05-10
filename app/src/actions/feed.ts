"use server";

import { type ActionResult, actionError } from "@/lib/errors";

/**
 * 子片 3c — Prism feed 域（feed_items + feed_sources + suggested_node 工作流）在 prism-0420 OpenAPI
 * 不存在（prism-0420 提供 /api/news 全局 + /api/news/{nid}/links/{node_id} 不带 status / 不带 sources 概念）。
 * 工作流不一一对应：punt 整体 NOT_IMPLEMENTED stub，签名保留以兼容 overview/settings/workspace 残留 import
 * （全在 eslint ignore / 子片 5 cleanup 时切换到 news 域或显式删除该域 UI）。
 */

const NOT_IMPLEMENTED = new Error(
  "feed_items 工作流在 prism-0420 OpenAPI 不存在（子片 5 后或 Phase 2.3 评估接 /api/news 域 or 删除 feed UI）",
);

export async function getFeedItems(_projectId: string, _status: string = "pending") {
  return [] as Array<Record<string, unknown>>;
}

export async function confirmFeedItem(
  _itemId: string,
  _nodeId: string,
): Promise<ActionResult<{ id: string }>> {
  return actionError(NOT_IMPLEMENTED);
}

export async function ignoreFeedItem(_itemId: string): Promise<ActionResult> {
  return actionError(NOT_IMPLEMENTED);
}

export async function reassignFeedItem(_itemId: string, _nodeId: string): Promise<ActionResult> {
  return actionError(NOT_IMPLEMENTED);
}

export async function getFeedItemsByNode(_projectId: string, _nodeId: string) {
  return [] as Array<Record<string, unknown>>;
}

export async function getFeedSources(_projectId: string) {
  return [] as Array<Record<string, unknown>>;
}

export async function createFeedSource(
  _projectId: string,
  _data: { sourceType: string; url: string; name: string },
): Promise<ActionResult<{ id: string }>> {
  return actionError(NOT_IMPLEMENTED);
}

export async function updateFeedSource(
  _sourceId: string,
  _data: { name?: string; url?: string; isActive?: boolean },
): Promise<ActionResult> {
  return actionError(NOT_IMPLEMENTED);
}

export async function deleteFeedSource(_sourceId: string): Promise<ActionResult> {
  return actionError(NOT_IMPLEMENTED);
}
