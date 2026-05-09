import { z } from "zod";

export const createTeamSchema = z.object({
  name: z.string().min(1, "团队名称不能为空").max(100, "团队名称最多 100 个字符").trim(),
  description: z.string().max(500, "描述最多 500 个字符").trim().optional(),
});

export const inviteMemberSchema = z.object({
  teamId: z.string().uuid("无效的团队 ID"),
  email: z.string().email("邮箱格式不正确").trim(),
  role: z.enum(["admin", "member"]).default("member"),
});

export type CreateTeamInput = z.infer<typeof createTeamSchema>;
export type InviteMemberInput = z.infer<typeof inviteMemberSchema>;
