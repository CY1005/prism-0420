import { z } from "zod";

export const ISSUE_CATEGORIES = ["bug", "tech_debt", "design_flaw", "performance"] as const;

const categorySchema = z.enum(ISSUE_CATEGORIES);

const tagsSchema = z
  .array(z.string().max(50, "单个标签最多 50 个字符").trim())
  .max(20, "最多 20 个标签")
  .optional();

export const createIssueSchema = z.object({
  projectId: z.string().uuid("无效的项目 ID"),
  nodeId: z.string().uuid().nullable(),
  category: categorySchema,
  title: z.string().min(1, "问题标题不能为空").max(200, "标题最多 200 个字符").trim(),
  description: z.string().min(1, "问题描述不能为空").max(5000, "问题描述最多 5000 个字符").trim(),
  tags: tagsSchema,
  assignedTo: z.string().uuid().optional(),
});

export const updateIssueSchema = z.object({
  issueId: z.string().uuid("无效的问题 ID"),
  projectId: z.string().uuid("无效的项目 ID"),
  title: z.string().min(1).max(200).trim().optional(),
  description: z
    .string()
    .min(1, "问题描述不能为空")
    .max(5000, "问题描述最多 5000 个字符")
    .trim()
    .optional(),
  tags: tagsSchema,
  nodeId: z.string().uuid().nullable().optional(),
  assignedTo: z.string().uuid().nullable().optional(),
});

export type CreateIssueInput = z.infer<typeof createIssueSchema>;
export type UpdateIssueInput = z.infer<typeof updateIssueSchema>;
