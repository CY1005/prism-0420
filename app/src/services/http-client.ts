/**
 * Shared HTTP client for FastAPI backend calls.
 * New service files should use these helpers instead of raw fetch.
 */

const BASE_URL = process.env.NEXT_PUBLIC_ANALYZER_URL || "http://localhost:8001";

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string };

export async function fetchJson<T>(path: string, options?: RequestInit): Promise<ApiResult<T>> {
  try {
    const resp = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
    if (!resp.ok) {
      const text = await resp.text();
      return { ok: false, error: `HTTP ${resp.status}: ${text}` };
    }
    const data = (await resp.json()) as T;
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `服务不可用: ${(e as Error).message}` };
  }
}

export async function postJson<T>(path: string, body: unknown): Promise<ApiResult<T>> {
  return fetchJson<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function patchJson<T>(path: string, body: unknown): Promise<ApiResult<T>> {
  return fetchJson<T>(path, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}
