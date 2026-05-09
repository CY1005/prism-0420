/**
 * Phase 2.2 子片 3a — 服务端 access token 获取（spec 06 §3 / α-P1 链路）。
 *
 * Server Component / Server Action 鉴权专用：
 * cookies().get('refresh_token') → POST /auth/refresh → access_token
 *
 * 同请求多次调用（一个 RSC 树 / 一个 Server Action 内）只触发一次 /auth/refresh
 * （`React.cache` 单请求 memo / 跨请求隔离 / 不持久化）。
 *
 * 不在客户端使用 / Client Components 走 services/http-client.ts（spec 06 §2 子片 1）。
 */

import { cookies } from "next/headers";
import { cache } from "react";
import type { components } from "@/types/api";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const REFRESH_COOKIE_NAME = "refresh_token";

export type ServerUser = components["schemas"]["UserProfile"];

/**
 * 获取当前请求的 access_token。
 * - 无 refresh cookie / refresh 失效 → 返 null（调用方 redirect /login 或抛 UnauthenticatedError）
 * - 同请求 React.cache 单次 memo
 */
export const getServerAccessToken = cache(async (): Promise<string | null> => {
  const cookieStore = await cookies();
  const refresh = cookieStore.get(REFRESH_COOKIE_NAME)?.value;
  if (!refresh) return null;

  const resp = await fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Cookie: `${REFRESH_COOKIE_NAME}=${refresh}` },
    body: JSON.stringify({}),
    cache: "no-store",
  });
  if (!resp.ok) return null;
  const data = (await resp.json()) as { access_token?: string };
  return typeof data.access_token === "string" ? data.access_token : null;
});

/**
 * 获取当前请求的 UserProfile（含 id / role / email / name）。
 * - 同请求 React.cache 单次 memo（与 getServerAccessToken 互不污染）
 * - access token 拿不到 / /auth/me 失败 → 返 null（调用方 redirect /login）
 */
export const getServerUser = cache(async (): Promise<ServerUser | null> => {
  const token = await getServerAccessToken();
  if (!token) return null;
  const resp = await fetch(`${BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!resp.ok) return null;
  return (await resp.json()) as ServerUser;
});
