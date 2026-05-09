import { z } from "zod";

export const createTeamSchema = z.object({
  name: z.string().min(1, "团队名称不能为空").max(100, "团队名称最多 100 个字符").trim(),
  description: z.string().max(500, "描述最多 500 个字符").trim().optional(),
});

export const updateTeamSchema = z.object({
  name: z.string().min(1, "团队名称不能为空").max(100, "团队名称最多 100 个字符").trim().optional(),
  description: z.string().max(500, "描述最多 500 个字符").trim().optional(),
  version: z.number().int().min(1, "版本号无效"),
});

// add by user_id：无候选下拉数据源（cross-sprint pool P22-4-backend-gap / Phase 2.3 接 user 检索）
export const addMemberSchema = z.object({
  user_id: z.string().uuid("无效的用户 ID"),
  role: z.enum(["admin", "member"]).default("member"),
});

export const updateMemberRoleSchema = z.object({
  role: z.enum(["admin", "member"]),
});

export const transferOwnershipSchema = z.object({
  new_owner_id: z.string().uuid("无效的用户 ID"),
});

export type CreateTeamInput = z.infer<typeof createTeamSchema>;
export type UpdateTeamInput = z.infer<typeof updateTeamSchema>;
export type AddMemberInput = z.infer<typeof addMemberSchema>;
export type UpdateMemberRoleInput = z.infer<typeof updateMemberRoleSchema>;
export type TransferOwnershipInput = z.infer<typeof transferOwnershipSchema>;
