/**
 * HTTP client for prism-0420 FastAPI backend.
 *
 * 锚点：design/01-engineering/06-frontend-spec.md §2 + ADR-004 P1 (Bearer JWT) + P3 (refresh cookie).
 * 范式：access token in-memory + Authorization Bearer header + credentials:'include' (refresh cookie 携带).
 * 401 路径：自动 POST /auth/refresh + retry 1 次 / refresh 失败抛 UnauthenticatedError 给上层.
 */

import { getAccessToken, setAccessToken, clearAccessToken } from "./auth-token-store";

// Phase 2.3 cleanup follow-up: 默认空字符串 = 同源相对路径
// 浏览器端 fetch("/auth/logout") → Next.js rewrites → backend
// 旧默认 "http://localhost:8000" 在远程访问时 = 客户机自己 localhost / 不通
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly errorCode: string | null,
    message: string,
    public readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class UnauthenticatedError extends ApiError {
  constructor(message = "Unauthenticated") {
    super(401, "unauthenticated", message);
    this.name = "UnauthenticatedError";
  }
}

interface FastApiErrorBody {
  detail?: unknown;
  error_code?: string;
  // B-P2-M14-workspace-dimension-error fix（dogfooding 2026-05-12）：backend
  // middleware 实际序列化字段名是 `code`（api/errors/middleware.py L18）；
  // 与 server-http-client.ts 同步增加 fallback 读取 + 保留 error_code 兼容老 mock。
  code?: string;
  message?: string;
}

async function parseError(resp: Response): Promise<ApiError> {
  let body: FastApiErrorBody = {};
  try {
    body = (await resp.json()) as FastApiErrorBody;
  } catch {
    // body 不是 json / 走 statusText
  }
  const errorCode =
    typeof body.error_code === "string"
      ? body.error_code
      : typeof body.code === "string"
        ? body.code
        : null;
  const message =
    (typeof body.message === "string" && body.message) ||
    (typeof body.detail === "string" && body.detail) ||
    resp.statusText ||
    `HTTP ${resp.status}`;
  if (resp.status === 401) {
    return new UnauthenticatedError(message);
  }
  return new ApiError(resp.status, errorCode, message, body.detail);
}

async function refreshAccessToken(): Promise<string | null> {
  // refresh cookie 由浏览器自动携带 (credentials: 'include').
  const resp = await fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!resp.ok) {
    clearAccessToken();
    return null;
  }
  const data = (await resp.json()) as { access_token?: string };
  if (typeof data.access_token === "string") {
    setAccessToken(data.access_token);
    return data.access_token;
  }
  return null;
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** 仅 retry 内部用 / 调用方不传 */
  _isRetry?: boolean;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, _isRetry, headers, ...rest } = options;
  const token = getAccessToken();
  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(headers as Record<string, string> | undefined),
  };
  if (token) {
    finalHeaders.Authorization = `Bearer ${token}`;
  }

  const resp = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    credentials: "include",
    headers: finalHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (resp.status === 401 && !_isRetry) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      return apiFetch<T>(path, { ...options, _isRetry: true });
    }
    throw new UnauthenticatedError();
  }

  if (!resp.ok) {
    throw await parseError(resp);
  }

  if (resp.status === 204) {
    return undefined as T;
  }

  return (await resp.json()) as T;
}

export const apiGet = <T>(path: string, options?: RequestOptions) =>
  apiFetch<T>(path, { ...options, method: "GET" });

export const apiPost = <T>(path: string, body?: unknown, options?: RequestOptions) =>
  apiFetch<T>(path, { ...options, method: "POST", body });

export const apiPatch = <T>(path: string, body?: unknown, options?: RequestOptions) =>
  apiFetch<T>(path, { ...options, method: "PATCH", body });

export const apiPut = <T>(path: string, body?: unknown, options?: RequestOptions) =>
  apiFetch<T>(path, { ...options, method: "PUT", body });

export const apiDelete = <T = void>(path: string, options?: RequestOptions) =>
  apiFetch<T>(path, { ...options, method: "DELETE" });

// 调用范式（types/api.ts paths/operations 集成）：
//   import type { paths } from "@/types/api";
//   type ProjectListResponse =
//     paths["/projects"]["get"]["responses"]["200"]["content"]["application/json"];
//   const data = await apiGet<ProjectListResponse>("/projects");
// 子片 3a-3c actions/* 改造时全走此范式，禁止裸 fetch。
