"use server";

import { db } from "@/db";
import { users } from "@/db/schema";
import { eq } from "drizzle-orm";
import bcrypt from "bcryptjs";
import { requireAuth } from "@/lib/auth";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";

async function requirePlatformAdmin() {
  const user = await requireAuth();
  if (user.role !== "platform_admin") {
    throw new AppError("无权限执行此操作", "blocking", "FORBIDDEN", 403);
  }
  return user;
}

export async function getUsers() {
  await requirePlatformAdmin();

  const userList = await db
    .select({
      id: users.id,
      name: users.name,
      email: users.email,
      role: users.role,
      status: users.status,
      createdAt: users.createdAt,
    })
    .from(users)
    .orderBy(users.createdAt);

  return userList;
}

export async function createUser(
  name: string,
  email: string,
  password: string,
): Promise<ActionResult<{ id: string }>> {
  try {
    const admin = await requirePlatformAdmin();

    if (!name.trim() || !email.trim() || !password) {
      return actionError(new AppError("所有字段必填", "blocking", "VALIDATION_ERROR"));
    }

    const [existing] = await db.select({ id: users.id }).from(users).where(eq(users.email, email));

    if (existing) {
      return actionError(new AppError("该邮箱已注册", "blocking", "DUPLICATE_ENTRY", 409));
    }

    const passwordHash = await bcrypt.hash(password, 12);
    const [newUser] = await db
      .insert(users)
      .values({ name: name.trim(), email: email.trim(), passwordHash })
      .returning({ id: users.id });

    logger.action("admin.createUser", admin.id, { targetUserId: newUser.id, email });
    return actionSuccess({ id: newUser.id });
  } catch (error) {
    return actionError(error);
  }
}

export async function toggleUserStatus(userId: string): Promise<ActionResult> {
  try {
    const admin = await requirePlatformAdmin();

    const [user] = await db
      .select({ id: users.id, status: users.status })
      .from(users)
      .where(eq(users.id, userId));

    if (!user) {
      return actionError(new AppError("用户不存在", "blocking", "NOT_FOUND", 404));
    }

    if (userId === admin.id) {
      return actionError(new AppError("不能禁用自己", "blocking", "VALIDATION_ERROR"));
    }

    const newStatus = user.status === "active" ? "disabled" : "active";
    await db
      .update(users)
      .set({
        status: newStatus,
        tokenInvalidatedAt: newStatus === "disabled" ? new Date() : null,
        updatedAt: new Date(),
      })
      .where(eq(users.id, userId));

    logger.action("admin.toggleUserStatus", admin.id, { targetUserId: userId, newStatus });
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function updateUserRole(userId: string, role: string): Promise<ActionResult> {
  try {
    const admin = await requirePlatformAdmin();

    const validRoles = ["user", "platform_admin"];
    if (!validRoles.includes(role)) {
      return actionError(new AppError("无效的角色", "blocking", "VALIDATION_ERROR"));
    }

    if (userId === admin.id) {
      return actionError(new AppError("不能修改自己的角色", "blocking", "VALIDATION_ERROR"));
    }

    await db.update(users).set({ role, updatedAt: new Date() }).where(eq(users.id, userId));

    logger.action("admin.updateUserRole", admin.id, { targetUserId: userId, role });
    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}
