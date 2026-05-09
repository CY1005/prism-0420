"use server";

import { requireAuth } from "@/lib/auth";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import { ErrorCode } from "@/lib/error-codes";

const API_BASE = process.env.API_URL ?? "http://localhost:8001";

// ─── Types ──────────────────────────────────────────

export interface TemplateContent {
  trigger_conditions: string[];
  analysis_steps: string[];
  pitfalls: string[];
  verification: string[];
  prompt_template: string;
}

export interface Template {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  category: string;
  content: TemplateContent;
  version: number;
  usage_count: number;
  last_used_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface TemplateVersion {
  id: string;
  version_number: number;
  content: TemplateContent;
  change_summary: string | null;
  created_by: string;
  created_at: string;
}

export interface TemplateMatchResult {
  template_id: string;
  name: string;
  description: string | null;
  category: string;
  similarity: number;
  usage_count: number;
}

// ─── Helper ─────────────────────────────────────────

async function fetchAPI(path: string, options: RequestInit = {}) {
  const user = await requireAuth();
  const token = process.env.INTERNAL_TOKEN ?? "";
  return fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Token": token,
      "X-User-Id": user.id,
      ...options.headers,
    },
  });
}

// ─── Actions ────────────────────────────────────────

export async function listTemplates(
  projectId: string,
  category?: string,
): Promise<ActionResult<{ templates: Template[]; total: number }>> {
  try {
    const params = new URLSearchParams({ project_id: projectId });
    if (category) params.set("category", category);
    const res = await fetchAPI(`/api/templates/?${params.toString()}`);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return actionError(
        new AppError(body.detail || "获取模板列表失败", "blocking", ErrorCode.INTERNAL_ERROR),
      );
    }
    return actionSuccess(await res.json());
  } catch (e) {
    return actionError(new AppError("获取模板列表失败", "blocking", ErrorCode.INTERNAL_ERROR));
  }
}

export async function getTemplate(templateId: string): Promise<ActionResult<Template>> {
  try {
    const res = await fetchAPI(`/api/templates/${templateId}`);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return actionError(
        new AppError(body.detail || "获取模板失败", "blocking", ErrorCode.INTERNAL_ERROR),
      );
    }
    return actionSuccess(await res.json());
  } catch (e) {
    return actionError(new AppError("获取模板失败", "blocking", ErrorCode.INTERNAL_ERROR));
  }
}

export async function createTemplate(data: {
  project_id: string;
  name: string;
  description?: string;
  category?: string;
  content: TemplateContent;
}): Promise<ActionResult<Template>> {
  try {
    const res = await fetchAPI("/api/templates/", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return actionError(
        new AppError(body.detail || "创建模板失败", "blocking", ErrorCode.INTERNAL_ERROR),
      );
    }
    return actionSuccess(await res.json());
  } catch (e) {
    return actionError(new AppError("创建模板失败", "blocking", ErrorCode.INTERNAL_ERROR));
  }
}

export async function updateTemplate(
  templateId: string,
  data: {
    name?: string;
    description?: string;
    category?: string;
    content?: TemplateContent;
    change_summary?: string;
  },
): Promise<ActionResult<Template>> {
  try {
    const res = await fetchAPI(`/api/templates/${templateId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return actionError(
        new AppError(body.detail || "更新模板失败", "blocking", ErrorCode.INTERNAL_ERROR),
      );
    }
    return actionSuccess(await res.json());
  } catch (e) {
    return actionError(new AppError("更新模板失败", "blocking", ErrorCode.INTERNAL_ERROR));
  }
}

export async function deleteTemplate(
  templateId: string,
): Promise<ActionResult<{ success: boolean }>> {
  try {
    const res = await fetchAPI(`/api/templates/${templateId}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return actionError(
        new AppError(body.detail || "删除模板失败", "blocking", ErrorCode.INTERNAL_ERROR),
      );
    }
    return actionSuccess(await res.json());
  } catch (e) {
    return actionError(new AppError("删除模板失败", "blocking", ErrorCode.INTERNAL_ERROR));
  }
}

export async function getTemplateHistory(
  templateId: string,
): Promise<ActionResult<TemplateVersion[]>> {
  try {
    const res = await fetchAPI(`/api/templates/${templateId}/history`);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return actionError(
        new AppError(body.detail || "获取版本历史失败", "blocking", ErrorCode.INTERNAL_ERROR),
      );
    }
    return actionSuccess(await res.json());
  } catch (e) {
    return actionError(new AppError("获取版本历史失败", "blocking", ErrorCode.INTERNAL_ERROR));
  }
}

export async function revertTemplate(
  templateId: string,
  targetVersion: number,
): Promise<ActionResult<Template>> {
  try {
    const params = new URLSearchParams({ target_version: String(targetVersion) });
    const res = await fetchAPI(`/api/templates/${templateId}/revert?${params.toString()}`, {
      method: "POST",
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return actionError(
        new AppError(body.detail || "回滚模板失败", "blocking", ErrorCode.INTERNAL_ERROR),
      );
    }
    return actionSuccess(await res.json());
  } catch (e) {
    return actionError(new AppError("回滚模板失败", "blocking", ErrorCode.INTERNAL_ERROR));
  }
}
