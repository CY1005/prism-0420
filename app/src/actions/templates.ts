"use server";

/* eslint-disable @typescript-eslint/no-unused-vars -- 子片 3c：templates CRUD 全函数 NOT_IMPLEMENTED stub（参数保留作子片 5+ 接 templates 后端域时的契约锚点 / 子片 5 cleanup 时由 CY 决定补端点 or 删页面） */
import { type ActionResult, actionError } from "@/lib/errors";

/**
 * 子片 3c — prism-0420 OpenAPI 暂未提供 templates CRUD endpoint
 * （仅 /api/projects/{pid}/cold-start/template singular 在 M11 域 / 不是 templates 库）。
 * 全函数 NOT_IMPLEMENTED stub，签名+类型保留以兼容 templates 页 / template-save-dialog 残留 import
 * （consumer 全在 eslint ignore / 子片 5 cleanup 时由 CY 决定补端点 or 删页面）。
 */

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

const NOT_IMPLEMENTED = new Error(
  "templates CRUD 在 prism-0420 OpenAPI 暂未提供（子片 5 后或 Phase 2.3 评估补端点）",
);

export async function listTemplates(
  _projectId: string,
  _category?: string,
): Promise<ActionResult<Template[]>> {
  return actionError(NOT_IMPLEMENTED);
}

export async function getTemplate(_templateId: string): Promise<ActionResult<Template>> {
  return actionError(NOT_IMPLEMENTED);
}

export async function createTemplate(_data: {
  projectId: string;
  name: string;
  description?: string;
  category: string;
  content: TemplateContent;
}): Promise<ActionResult<{ id: string }>> {
  return actionError(NOT_IMPLEMENTED);
}

export async function updateTemplate(
  _templateId: string,
  _data: {
    name?: string;
    description?: string;
    category?: string;
    content?: TemplateContent;
    changeSummary?: string;
  },
): Promise<ActionResult> {
  return actionError(NOT_IMPLEMENTED);
}

export async function deleteTemplate(_templateId: string): Promise<ActionResult> {
  return actionError(NOT_IMPLEMENTED);
}

export async function getTemplateHistory(
  _templateId: string,
): Promise<ActionResult<TemplateVersion[]>> {
  return actionError(NOT_IMPLEMENTED);
}

export async function revertTemplate(
  _templateId: string,
  _versionId: string,
): Promise<ActionResult> {
  return actionError(NOT_IMPLEMENTED);
}
