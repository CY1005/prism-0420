import { db } from "@/db";
import { projectMembers, users } from "@/db/schema";
import { eq, and } from "drizzle-orm";
import { AppError } from "@/lib/errors";

export type ProjectRole = "admin" | "editor" | "viewer";

const ROLE_HIERARCHY: Record<ProjectRole, number> = {
  admin: 3,
  editor: 2,
  viewer: 1,
};

/**
 * 检查用户是否有项目权限
 * platform_admin 直接放行
 */
export async function checkProjectAccess(
  userId: string,
  projectId: string,
  requiredRole: ProjectRole,
): Promise<void> {
  // 检查是否是平台管理员
  const [user] = await db.select({ role: users.role }).from(users).where(eq(users.id, userId));

  if (user?.role === "platform_admin") return;

  // 查项目成员权限
  const [member] = await db
    .select({ role: projectMembers.role })
    .from(projectMembers)
    .where(and(eq(projectMembers.projectId, projectId), eq(projectMembers.userId, userId)));

  if (!member) {
    throw new AppError("无权限访问此项目", "blocking", "FORBIDDEN", 403);
  }

  const memberLevel = ROLE_HIERARCHY[member.role as ProjectRole] || 0;
  const requiredLevel = ROLE_HIERARCHY[requiredRole];

  if (memberLevel < requiredLevel) {
    throw new AppError("权限不足", "blocking", "FORBIDDEN", 403);
  }
}

/**
 * 检查是否是平台管理员
 */
export async function requirePlatformAdmin(userId: string): Promise<void> {
  const [user] = await db.select({ role: users.role }).from(users).where(eq(users.id, userId));

  if (user?.role !== "platform_admin") {
    throw new AppError("需要平台管理员权限", "blocking", "FORBIDDEN", 403);
  }
}
