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
  description: z.string().min(1, "问题描述不能为空").max(5000, "问题描述最多 5000 个字符").trim(),
  tags: tagsSchema,
});

export const updateIssueSchema = z.object({
  issueId: z.string().uuid("无效的问题 ID"),
  category: categorySchema.optional(),
  description: z
    .string()
    .min(1, "问题描述不能为空")
    .max(5000, "问题描述最多 5000 个字符")
    .trim()
    .optional(),
  tags: tagsSchema,
});

export type CreateIssueInput = z.infer<typeof createIssueSchema>;
export type UpdateIssueInput = z.infer<typeof updateIssueSchema>;
