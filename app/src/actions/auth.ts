"use server";

import { db } from "@/db";
import { users } from "@/db/schema";
import { eq } from "drizzle-orm";
import bcrypt from "bcryptjs";
import { signIn, signOut, auth } from "@/lib/auth";
import { registerSchema } from "@/lib/validators/auth";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess } from "@/lib/errors";

export async function register(formData: FormData): Promise<ActionResult<{ id: string }>> {
  try {
    const raw = {
      name: formData.get("name") as string,
      email: formData.get("email") as string,
      password: formData.get("password") as string,
    };

    const parsed = registerSchema.safeParse(raw);
    if (!parsed.success) {
      const firstError = parsed.error.issues[0]?.message || "输入格式错误";
      return actionError(new Error(firstError));
    }

    const { name, email, password } = parsed.data;

    // 检查邮箱是否已注册
    const [existing] = await db.select({ id: users.id }).from(users).where(eq(users.email, email));

    if (existing) {
      return {
        success: false,
        error: "该邮箱已注册",
        code: "DUPLICATE_ENTRY",
        severity: "blocking",
      };
    }

    const passwordHash = await bcrypt.hash(password, 12);

    const [newUser] = await db
      .insert(users)
      .values({ name, email, passwordHash })
      .returning({ id: users.id });

    logger.info("auth.register", { userId: newUser.id, email });

    // 自动登录
    await signIn("credentials", {
      email,
      password,
      redirect: false,
    });

    return actionSuccess({ id: newUser.id });
  } catch (error) {
    return actionError(error);
  }
}

export async function login(_prevState: unknown, formData: FormData): Promise<{ error?: string }> {
  try {
    const email = formData.get("email") as string;

    // AC5: 禁用账号检查，返回明确提示
    const [user] = await db
      .select({ status: users.status })
      .from(users)
      .where(eq(users.email, email));

    if (user?.status === "disabled") {
      return { error: "账号已被禁用，请联系管理员" };
    }

    await signIn("credentials", {
      email,
      password: formData.get("password") as string,
      redirectTo: "/projects",
    });
    return {};
  } catch (error) {
    if (error instanceof Error && error.message.includes("NEXT_REDIRECT")) {
      throw error; // let Next.js handle redirect
    }
    return { error: "邮箱或密码错误" };
  }
}

export async function logout() {
  await signOut({ redirectTo: "/login" });
}

export async function getSessionUser(): Promise<{
  id: string;
  name: string;
  email: string;
  role: string;
} | null> {
  const session = await auth();
  if (!session?.user?.id) return null;
  return session.user as { id: string; name: string; email: string; role: string };
}
