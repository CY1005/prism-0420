import { z } from "zod";

export const createProjectSchema = z.object({
  name: z.string().min(1, "请输入项目名称").max(100, "项目名称最多100个字符").trim(),
  description: z.string().max(500, "描述最多500个字符").optional(),
  templateType: z.enum(["product_analysis", "system_architecture", "research_platform", "custom"]),
});

export const updateProjectSchema = z.object({
  name: z.string().min(1, "项目名称不能为空").max(100, "项目名称最多100个字符").trim().optional(),
  description: z.string().max(500).optional(),
});

export type CreateProjectInput = z.infer<typeof createProjectSchema>;
export type UpdateProjectInput = z.infer<typeof updateProjectSchema>;
