"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  serverApiGet,
  serverApiPost,
  serverApiPut,
  serverApiDelete,
  UnauthenticatedError,
} from "@/lib/server-http-client";
import { getServerUser } from "@/lib/server-auth";
import { createProjectSchema } from "@/lib/validators/project";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import type { components } from "@/types/api";

/**
 * Server-side 读 helper：UnauthenticatedError 直接 redirect /login（spec 06 §3 字面）。
 * 其他错误透出给 caller 决定（toast / error.tsx）。
 */
async function withAuthRedirect<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    if (error instanceof UnauthenticatedError) {
      redirect("/login");
    }
    throw error;
  }
}

type ProjectResponse = components["schemas"]["ProjectResponse"];
type ProjectListResponse = components["schemas"]["ProjectListResponse"];
type ProjectCreate = components["schemas"]["ProjectCreate"];
type ProjectUpdate = components["schemas"]["ProjectUpdate"];
type MemberListResponse = components["schemas"]["MemberListResponse"];
type MemberResponse = components["schemas"]["MemberResponse"];
type MemberRole = components["schemas"]["MemberRoleEnum"];

export async function getProjects(): Promise<ProjectResponse[]> {
  return withAuthRedirect(async () => {
    const data = await serverApiGet<ProjectListResponse>("/api/projects");
    return data.items;
  });
}

export async function getProject(projectId: string): Promise<ProjectResponse | null> {
  return withAuthRedirect(async () => {
    try {
      return await serverApiGet<ProjectResponse>(`/api/projects/${projectId}`);
    } catch (error) {
      if (error instanceof UnauthenticatedError) throw error;
      return null;
    }
  });
}

export async function createProject(formData: FormData): Promise<ActionResult<{ id: string }>> {
  try {
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
    const body: ProjectCreate = {
      name,
      description: description ?? null,
      template_type: templateType,
    };

    const project = await serverApiPost<ProjectResponse>("/api/projects", body);

    logger.action("project.create", "self", { projectId: project.id, templateType });
    revalidatePath("/");

    return actionSuccess({ id: project.id });
  } catch (error) {
    return actionError(error);
  }
}

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
    if (data.name !== undefined && data.name.trim() === "") {
      return actionError(new AppError("项目名称不能为空", "blocking", "VALIDATION_ERROR"));
    }

    const body: ProjectUpdate = {
      ...(data.name !== undefined && { name: data.name.trim() }),
      ...(data.description !== undefined && { description: data.description }),
      ...(data.hierarchyLabels !== undefined && { hierarchy_labels: data.hierarchyLabels }),
      ...(data.versionMode !== undefined && { version_mode: data.versionMode }),
    };

    await serverApiPut<ProjectResponse>(`/api/projects/${projectId}`, body);

    logger.action("project.update", "self", { projectId });
    revalidatePath(`/projects/${projectId}`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function getProjectMembers(projectId: string): Promise<MemberResponse[]> {
  return withAuthRedirect(async () => {
    const data = await serverApiGet<MemberListResponse>(`/api/projects/${projectId}/members`);
    return data.items;
  });
}

export async function addProjectMember(
  projectId: string,
  userId: string,
  role: MemberRole = "viewer",
): Promise<ActionResult<{ id: string }>> {
  try {
    const member = await serverApiPost<MemberResponse>(`/api/projects/${projectId}/members`, {
      user_id: userId,
      role,
    });

    logger.action("project.addMember", "self", { projectId, targetUserId: userId, role });
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
    await serverApiDelete(`/api/projects/${projectId}/members/${userId}`);

    logger.action("project.removeMember", "self", { projectId, removedUserId: userId });
    revalidatePath(`/projects/${projectId}/settings`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function getMyProjectRole(projectId: string): Promise<MemberRole | null> {
  const me = await getServerUser();
  if (!me) return null;
  if (me.role === "platform_admin") return "owner";

  try {
    const project = await serverApiGet<ProjectResponse>(`/api/projects/${projectId}`);
    if (project.owner_id === me.id) return "owner";
  } catch {
    return null;
  }

  try {
    const members = await getProjectMembers(projectId);
    const mine = members.find((m) => m.user_id === me.id);
    return mine?.role ?? null;
  } catch {
    return null;
  }
}

export async function updateProjectAIConfig(
  projectId: string,
  provider: string,
  apiKeyPlain: string | null,
): Promise<ActionResult> {
  try {
    const validProviders = ["local", "claude", "codex", "kimi", "deepseek"];
    if (!validProviders.includes(provider)) {
      return actionError(new AppError("无效的AI提供商", "blocking", "VALIDATION_ERROR"));
    }

    const body: components["schemas"]["AiProviderUpdate"] = {
      ai_provider: provider,
      ai_api_key: apiKeyPlain,
    };
    await serverApiPut(`/api/projects/${projectId}/ai-provider`, body);

    logger.action("project.updateAIConfig", "self", { projectId, provider });
    revalidatePath(`/projects/${projectId}/settings`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}
