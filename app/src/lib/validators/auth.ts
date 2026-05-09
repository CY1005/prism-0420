import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("邮箱格式不正确"),
  password: z.string().min(1, "请输入密码"),
});

export const registerSchema = z.object({
  name: z.string().min(2, "用户名至少2个字符").max(50, "用户名最多50个字符").trim(),
  email: z.string().email("邮箱格式不正确").trim(),
  password: z.string().min(8, "密码至少8个字符").max(100, "密码最多100个字符"),
});

export type LoginInput = z.infer<typeof loginSchema>;
export type RegisterInput = z.infer<typeof registerSchema>;
