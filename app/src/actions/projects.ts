"use server";

import { db } from "@/db";
import {
  projects,
  nodes,
  projectDimensionConfigs,
  dimensionTypes,
  projectTemplates,
  projectMembers,
  users,
} from "@/db/schema";
import { eq, count, and, isNull } from "drizzle-orm";
import { revalidatePath } from "next/cache";
import { requireAuth } from "@/lib/auth";
import { checkProjectAccess } from "@/services/permission.service";
import { createProjectSchema } from "@/lib/validators/project";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";

export async function getProjects() {
  const user = await requireAuth();

  // 平台管理员看所有项目，普通用户只看自己有权限的
  // F2 AC6: 已软删除的项目不在列表中显示
  let projectList;
  if (user.role === "platform_admin") {
    projectList = await db.select().from(projects).where(isNull(projects.deletedAt));
  } else {
    projectList = await db
      .select({ project: projects })
      .from(projects)
      .innerJoin(projectMembers, eq(projects.id, projectMembers.projectId))
      .where(and(eq(projectMembers.userId, user.id), isNull(projects.deletedAt)))
      .then((rows) => rows.map((r) => r.project));
  }

  const result = await Promise.all(
    projectList.map(async (project) => {
      const [nodeCount] = await db
        .select({ count: count() })
        .from(nodes)
        .where(eq(nodes.projectId, project.id));

      return {
        ...project,
        nodeCount: nodeCount.count,
      };
    }),
  );

  return result;
}

export async function getProject(projectId: string) {
  const user = await requireAuth();
  await checkProjectAccess(user.id, projectId, "viewer");

  const [project] = await db.select().from(projects).where(eq(projects.id, projectId));
  return project ?? null;
}

export async function createProject(formData: FormData): Promise<ActionResult<{ id: string }>> {
  try {
    const user = await requireAuth();

    const raw = {
      name: formData.get("name") as string,
      description: (formData.get("description") as string) || undefined,
      templateType: formData.get("templateType") as string,
    };

    const parsed = createProjectSchema.safeParse(raw);
    if (!parsed.success) {
      return actionError(
        new AppError(
          parsed.error.issues[0]?.message || "输入格式错误",
          "blocking",
          "VALIDATION_ERROR",
        ),
      );
    }

    const { name, description, templateType } = parsed.data;

    // 获取模板配置
    const [template] = await db
      .select()
      .from(projectTemplates)
      .where(eq(projectTemplates.key, templateType));

    if (!template) {
      return actionError(new AppError("无效的项目模板", "blocking", "VALIDATION_ERROR"));
    }

    // 事务：创建项目 + 维度配置 + 创建者成员
    const result = await db.transaction(async (tx) => {
      const [newProject] = await tx
        .insert(projects)
        .values({
          name,
          description,
          templateType,
          hierarchyLabels: template.hierarchyLabels,
          createdBy: user.id,
        })
        .returning();

      // 获取模板维度并创建配置
      // 用 in 查询模板的维度keys不太方便，先查全部再filter
      const allDims = await tx.select().from(dimensionTypes);
      const enabledDims = allDims.filter((d) => template.dimensionKeys.includes(d.key));

      if (enabledDims.length > 0) {
        await tx.insert(projectDimensionConfigs).values(
          enabledDims.map((dim, i) => ({
            projectId: newProject.id,
            dimensionTypeId: dim.id,
            enabled: true,
            sortOrder: i,
          })),
        );
      }

      // 创建者自动成为项目管理员
      await tx.insert(projectMembers).values({
        projectId: newProject.id,
        userId: user.id,
        role: "admin",
      });

      return newProject;
    });

    logger.action("project.create", user.id, { projectId: result.id, templateType });
    revalidatePath("/");

    return actionSuccess({ id: result.id });
  } catch (error) {
    return actionError(error);
  }
}

// ─── Project Settings ─────────────────────────────────

export async function updateProject(
  projectId: string,
  data: {
    name?: string;
    description?: string;
    hierarchyLabels?: string[];
    versionMode?: string;
  },
): Promise<ActionResult> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "admin");

    if (data.name !== undefined && data.name.trim() === "") {
      return actionError(new AppError("项目名称不能为空", "blocking", "VALIDATION_ERROR"));
    }

    await db
      .update(projects)
      .set({
        ...(data.name !== undefined && { name: data.name.trim() }),
        ...(data.description !== undefined && { description: data.description }),
        ...(data.hierarchyLabels !== undefined && { hierarchyLabels: data.hierarchyLabels }),
        ...(data.versionMode !== undefined && { versionMode: data.versionMode }),
        updatedAt: new Date(),
      })
      .where(eq(projects.id, projectId));

    logger.action("project.update", user.id, { projectId });
    revalidatePath(`/projects/${projectId}`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function getProjectMembers(projectId: string) {
  const user = await requireAuth();
  await checkProjectAccess(user.id, projectId, "viewer");

  const members = await db
    .select({
      id: projectMembers.id,
      userId: projectMembers.userId,
      role: projectMembers.role,
      createdAt: projectMembers.createdAt,
      userName: users.name,
      userEmail: users.email,
    })
    .from(projectMembers)
    .innerJoin(users, eq(projectMembers.userId, users.id))
    .where(eq(projectMembers.projectId, projectId));

  return members;
}

export async function addProjectMember(
  projectId: string,
  email: string,
  role: string,
): Promise<ActionResult<{ id: string }>> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "admin");

    // 查找目标用户
    const [targetUser] = await db.select().from(users).where(eq(users.email, email));

    if (!targetUser) {
      return actionError(new AppError("未找到该邮箱对应的用户", "blocking", "NOT_FOUND", 404));
    }

    // 检查是否已是成员
    const [existing] = await db
      .select()
      .from(projectMembers)
      .where(
        and(eq(projectMembers.projectId, projectId), eq(projectMembers.userId, targetUser.id)),
      );

    if (existing) {
      return actionError(new AppError("该用户已是项目成员", "blocking", "DUPLICATE_ENTRY", 409));
    }

    const [member] = await db
      .insert(projectMembers)
      .values({
        projectId,
        userId: targetUser.id,
        role,
      })
      .returning();

    logger.action("project.addMember", user.id, { projectId, targetUserId: targetUser.id, role });
    revalidatePath(`/projects/${projectId}/settings`);

    return actionSuccess({ id: member.id });
  } catch (error) {
    return actionError(error);
  }
}

export async function removeProjectMember(
  projectId: string,
  userId: string,
): Promise<ActionResult> {
  try {
    const currentUser = await requireAuth();
    await checkProjectAccess(currentUser.id, projectId, "admin");

    // 不允许移除自己（项目至少需要一个管理员）
    if (userId === currentUser.id) {
      return actionError(new AppError("不能移除自己", "blocking", "VALIDATION_ERROR"));
    }

    const [member] = await db
      .select()
      .from(projectMembers)
      .where(and(eq(projectMembers.projectId, projectId), eq(projectMembers.userId, userId)));

    if (!member) {
      return actionError(new AppError("该用户不是项目成员", "blocking", "NOT_FOUND", 404));
    }

    await db
      .delete(projectMembers)
      .where(and(eq(projectMembers.projectId, projectId), eq(projectMembers.userId, userId)));

    logger.action("project.removeMember", currentUser.id, { projectId, removedUserId: userId });
    revalidatePath(`/projects/${projectId}/settings`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function getMyProjectRole(
  projectId: string,
): Promise<"admin" | "editor" | "viewer" | null> {
  const user = await requireAuth();

  if (user.role === "platform_admin") return "admin";

  const [member] = await db
    .select({ role: projectMembers.role })
    .from(projectMembers)
    .where(and(eq(projectMembers.projectId, projectId), eq(projectMembers.userId, user.id)));

  if (!member) return null;

  const role = member.role as "admin" | "editor" | "viewer";
  return role;
}

export async function updateProjectAIConfig(
  projectId: string,
  provider: string,
  apiKeyPlain: string | null,
): Promise<ActionResult> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "admin");

    const validProviders = ["local", "claude", "codex", "kimi", "deepseek"];
    if (!validProviders.includes(provider)) {
      return actionError(new AppError("无效的AI提供商", "blocking", "VALIDATION_ERROR"));
    }

    // Bug #7 fix: encrypt API key before storing
    let encryptedKey: string | null = null;
    if (apiKeyPlain) {
      try {
        const { encryptApiKey } = await import("@/lib/crypto");
        encryptedKey = encryptApiKey(apiKeyPlain);
      } catch {
        // If encryption secret not configured, store null and warn
        logger.warn("project.updateAIConfig", { reason: "encryption_key_not_configured" });
        return actionError(
          new AppError("加密密钥未配置，无法保存API Key", "blocking", "VALIDATION_ERROR"),
        );
      }
    }

    await db
      .update(projects)
      .set({
        aiProvider: provider,
        aiApiKeyEnc: encryptedKey,
        updatedAt: new Date(),
      })
      .where(eq(projects.id, projectId));

    logger.action("project.updateAIConfig", user.id, { projectId, provider });
    revalidatePath(`/projects/${projectId}/settings`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}
