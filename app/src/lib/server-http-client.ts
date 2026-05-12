/**
 * Phase 2.2 子片 3a — 服务端 fetch wrapper（spec 06 §3 / α-P1 链路）。
 *
 * Server Component / Server Action 调用后端业务 endpoint：
 * getServerAccessToken() → Authorization: Bearer → fetch backend
 *
 * 与 services/http-client.ts（客户端）API 对齐 / 错误类型复用 ApiError + UnauthenticatedError。
 * 401 不自动 retry：refresh 已在 getServerAccessToken 处理 / Server 端无第二次机会。
 *
 * 不在客户端使用 / Client Components 走 services/http-client.ts（spec 06 §2 子片 1）。
 */

import { getServerAccessToken } from "./server-auth";
import { ApiError, UnauthenticatedError } from "@/services/http-client";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

interface FastApiErrorBody {
  detail?: unknown;
  error_code?: string;
  // B-P2-M14-workspace-dimension-error fix（dogfooding 2026-05-12）：backend
  // api/errors/middleware.py L18 实际序列化字段名是 `code` 而非 `error_code`；
  // 历史 parser 只看 error_code → ApiError.errorCode 全 null → 业务侧无法按 code 分发
  // UX（如 OverviewNoDimensionsError 优雅降级为空 tree）。新增 `code` 字段读取，
  // 保留 `error_code` 兼容老 mock（server-http-client.test.ts L78）+ 未来契约迁移空间。
  code?: string;
  message?: string;
}

async function parseError(resp: Response): Promise<ApiError> {
  let body: FastApiErrorBody = {};
  try {
    body = (await resp.json()) as FastApiErrorBody;
  } catch {
    // 非 json body
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

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
}

export async function serverApiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options;
  const token = await getServerAccessToken();
  if (!token) {
    throw new UnauthenticatedError(
      "no server-side access token (refresh cookie missing or expired)",
    );
  }
  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
    ...(headers as Record<string, string> | undefined),
  };

  const resp = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: finalHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });

  if (!resp.ok) {
    throw await parseError(resp);
  }
  if (resp.status === 204) {
    return undefined as T;
  }
  return (await resp.json()) as T;
}

export const serverApiGet = <T>(path: string, options?: RequestOptions) =>
  serverApiFetch<T>(path, { ...options, method: "GET" });

export const serverApiPost = <T>(path: string, body?: unknown, options?: RequestOptions) =>
  serverApiFetch<T>(path, { ...options, method: "POST", body });

export const serverApiPatch = <T>(path: string, body?: unknown, options?: RequestOptions) =>
  serverApiFetch<T>(path, { ...options, method: "PATCH", body });

export const serverApiPut = <T>(path: string, body?: unknown, options?: RequestOptions) =>
  serverApiFetch<T>(path, { ...options, method: "PUT", body });

export const serverApiDelete = <T = void>(path: string, options?: RequestOptions) =>
  serverApiFetch<T>(path, { ...options, method: "DELETE" });

/**
 * 文件下载响应（M19 export 等场景）：response body 是 text/binary，filename 在
 * Content-Disposition header。返回 {filename, content} 给消费方直接构造 Blob + a.download。
 *
 * Why：M19 export 后端走标准 HTTP attachment（text/markdown bytes + Content-Disposition），
 * 而非 JSON wrapper。serverApiPost 默认 res.json() 会失败，留 ExportPayload=unknown 让消费方
 * 裸用 result.data.content（P22-3c-6 punt 真因 = 前端 client wrapper 不支持文本/二进制响应，
 * 不是后端 schema 缺失 / 02-quality-spec.md §HTTP-Client 立规）。
 */
export interface DownloadResponse {
  filename: string;
  content: string;
}

const _CD_FILENAME_RE = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i;

function parseFilename(disposition: string | null): string {
  if (!disposition) return "download.bin";
  const match = _CD_FILENAME_RE.exec(disposition);
  return match?.[1]?.trim() || "download.bin";
}

export async function serverApiPostDownload(
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<DownloadResponse> {
  const { headers, ...rest } = options;
  const token = await getServerAccessToken();
  if (!token) {
    throw new UnauthenticatedError(
      "no server-side access token (refresh cookie missing or expired)",
    );
  }
  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
    ...(headers as Record<string, string> | undefined),
  };

  const resp = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    method: "POST",
    headers: finalHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });

  if (!resp.ok) {
    throw await parseError(resp);
  }

  const filename = parseFilename(resp.headers.get("Content-Disposition"));
  const content = await resp.text();
  return { filename, content };
}

export { ApiError, UnauthenticatedError };
