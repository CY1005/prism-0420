"use server";

import { revalidatePath } from "next/cache";
import {
  serverApiGet,
  serverApiPost,
  serverApiPatch,
  serverApiDelete,
  UnauthenticatedError,
} from "@/lib/server-http-client";
import {
  createTeamSchema,
  updateTeamSchema,
  addMemberSchema,
  updateMemberRoleSchema,
  transferOwnershipSchema,
} from "@/lib/validators/team";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import { ErrorCode } from "@/lib/error-codes";
import type { components } from "@/types/api";
import { withAuthRedirect } from "@/lib/server-action-helpers";

type TeamRead = components["schemas"]["TeamRead"];
type TeamCreate = components["schemas"]["TeamCreate"];
type TeamUpdate = components["schemas"]["TeamUpdate"];
type TeamMemberAdd = components["schemas"]["TeamMemberAdd"];
type TeamMemberRoleUpdate = components["schemas"]["TeamMemberRoleUpdate"];
type TeamTransferOwnership = components["schemas"]["TeamTransferOwnership"];
type TeamMemberRemoveResponse = components["schemas"]["TeamMemberRemoveResponse"];

// ─── reads ──────────────────────────────────────────

export async function getTeams(): Promise<TeamRead[]> {
  return withAuthRedirect(() => serverApiGet<TeamRead[]>("/api/teams"));
}

export async function getTeam(teamId: string): Promise<TeamRead | null> {
  return withAuthRedirect(async () => {
    try {
      return await serverApiGet<TeamRead>(`/api/teams/${teamId}`);
    } catch (error) {
      if (error instanceof UnauthenticatedError) throw error;
      return null;
    }
  });
}

// isTeamOwner 已删（Phase 2.3 子 sprint C / P22-4-2 关闭 / 无 caller 死代码 / 页面直接 creator_id === me.id 推断）

// ─── mutations ─────────────────────────────────────

export async function createTeam(formData: FormData): Promise<ActionResult<{ id: string }>> {
  try {
    const raw = {
      name: formData.get("name") as string,
      description: ((formData.get("description") as string) || "").trim() || undefined,
    };
    const parsed = createTeamSchema.safeParse(raw);
    if (!parsed.success) {
      return actionError(
        new AppError(
          parsed.error.issues[0]?.message || "输入格式错误",
          "blocking",
          ErrorCode.VALIDATION_ERROR,
        ),
      );
    }

    const body: TeamCreate = {
      name: parsed.data.name,
      description: parsed.data.description ?? null,
    };
    const team = await serverApiPost<TeamRead>("/api/teams", body);

    logger.action("team.create", "self", { teamId: team.id });
    revalidatePath("/teams");

    return actionSuccess({ id: team.id });
  } catch (error) {
    return actionError(error);
  }
}

export async function updateTeam(
  teamId: string,
  data: { name?: string; description?: string | null; version: number },
): Promise<ActionResult> {
  try {
    const parsed = updateTeamSchema.safeParse(data);
    if (!parsed.success) {
      return actionError(
        new AppError(
          parsed.error.issues[0]?.message || "输入格式错误",
          "blocking",
          ErrorCode.VALIDATION_ERROR,
        ),
      );
    }

    const body: TeamUpdate = {
      ...(parsed.data.name !== undefined && { name: parsed.data.name }),
      ...(parsed.data.description !== undefined && { description: parsed.data.description }),
      version: parsed.data.version,
    };
    await serverApiPatch<TeamRead>(`/api/teams/${teamId}`, body);

    logger.action("team.update", "self", { teamId });
    revalidatePath(`/teams/${teamId}`);
    revalidatePath("/teams");

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function deleteTeam(teamId: string): Promise<ActionResult> {
  try {
    await serverApiDelete(`/api/teams/${teamId}`);

    logger.action("team.delete", "self", { teamId });
    revalidatePath("/teams");

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function transferOwnership(teamId: string, newOwnerId: string): Promise<ActionResult> {
  try {
    const parsed = transferOwnershipSchema.safeParse({ new_owner_id: newOwnerId });
    if (!parsed.success) {
      return actionError(
        new AppError(
          parsed.error.issues[0]?.message || "输入格式错误",
          "blocking",
          ErrorCode.VALIDATION_ERROR,
        ),
      );
    }

    const body: TeamTransferOwnership = { new_owner_id: parsed.data.new_owner_id };
    await serverApiPost(`/api/teams/${teamId}/transfer-ownership`, body);

    logger.action("team.transferOwnership", "self", { teamId, newOwnerId });
    revalidatePath(`/teams/${teamId}`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function addMember(
  teamId: string,
  userId: string,
  role: "admin" | "member" = "member",
): Promise<ActionResult<{ id: string }>> {
  try {
    const parsed = addMemberSchema.safeParse({ user_id: userId, role });
    if (!parsed.success) {
      return actionError(
        new AppError(
          parsed.error.issues[0]?.message || "输入格式错误",
          "blocking",
          ErrorCode.VALIDATION_ERROR,
        ),
      );
    }

    const body: TeamMemberAdd = { user_id: parsed.data.user_id, role: parsed.data.role };
    const member = await serverApiPost<{ id: string }>(`/api/teams/${teamId}/members`, body);

    logger.action("team.addMember", "self", { teamId, targetUserId: userId, role });
    revalidatePath(`/teams/${teamId}`);

    return actionSuccess({ id: member.id });
  } catch (error) {
    return actionError(error);
  }
}

export async function updateMemberRole(
  teamId: string,
  userId: string,
  role: "admin" | "member",
): Promise<ActionResult> {
  try {
    const parsed = updateMemberRoleSchema.safeParse({ role });
    if (!parsed.success) {
      return actionError(
        new AppError(
          parsed.error.issues[0]?.message || "输入格式错误",
          "blocking",
          ErrorCode.VALIDATION_ERROR,
        ),
      );
    }

    const body: TeamMemberRoleUpdate = { role: parsed.data.role };
    await serverApiPatch(`/api/teams/${teamId}/members/${userId}`, body);

    logger.action("team.updateMemberRole", "self", { teamId, targetUserId: userId, role });
    revalidatePath(`/teams/${teamId}`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

/**
 * project 归属变更（M20 own 独立端点 / POST /api/projects/{pid}/move-team）。
 * targetTeamId=null → 移回个人；非 null → 加入 team。
 */
export async function moveProjectTeam(
  projectId: string,
  targetTeamId: string | null,
): Promise<ActionResult> {
  try {
    await serverApiPost(`/api/projects/${projectId}/move-team`, {
      target_team_id: targetTeamId,
    });

    logger.action("team.moveProject", "self", { projectId, targetTeamId });
    revalidatePath(`/projects/${projectId}/settings`);
    revalidatePath("/teams");

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

export async function removeMember(
  teamId: string,
  userId: string,
): Promise<ActionResult<TeamMemberRemoveResponse>> {
  try {
    const result = await serverApiDelete<TeamMemberRemoveResponse>(
      `/api/teams/${teamId}/members/${userId}`,
    );

    logger.action("team.removeMember", "self", {
      teamId,
      removedUserId: userId,
      residualCount: result?.residual_count ?? 0,
    });
    revalidatePath(`/teams/${teamId}`);

    return actionSuccess(result);
  } catch (error) {
    return actionError(error);
  }
}
