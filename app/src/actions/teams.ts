"use server";

import { db } from "@/db";
import { teams, teamMembers, users, projects } from "@/db/schema";
import { eq, and } from "drizzle-orm";
import { revalidatePath } from "next/cache";
import { requireAuth } from "@/lib/auth";
import { checkProjectAccess } from "@/services/permission.service";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import { ErrorCode } from "@/lib/error-codes";
import { defineAction } from "@/lib/define-action";
import { createTeamSchema, inviteMemberSchema } from "@/lib/validators/team";

// ─── getTeams ────────────────────────────────────────

export async function getTeams() {
  const user = await requireAuth();

  // Teams the user owns or is a member of
  const ownedTeams = await db.select().from(teams).where(eq(teams.ownerId, user.id));

  const memberships = await db
    .select({ team: teams })
    .from(teamMembers)
    .innerJoin(teams, eq(teamMembers.teamId, teams.id))
    .where(eq(teamMembers.userId, user.id));

  // Deduplicate
  const teamMap = new Map<string, (typeof ownedTeams)[0]>();
  for (const t of ownedTeams) teamMap.set(t.id, t);
  for (const { team } of memberships) teamMap.set(team.id, team);

  return Array.from(teamMap.values());
}

// ─── getTeamById ─────────────────────────────────────

export async function getTeamById(teamId: string) {
  const user = await requireAuth();

  const [team] = await db.select().from(teams).where(eq(teams.id, teamId));
  if (!team) {
    throw new AppError("团队不存在", "blocking", "NOT_FOUND", 404);
  }

  const members = await db
    .select({
      id: teamMembers.id,
      userId: teamMembers.userId,
      role: teamMembers.role,
      joinedAt: teamMembers.joinedAt,
      userName: users.name,
      userEmail: users.email,
    })
    .from(teamMembers)
    .innerJoin(users, eq(teamMembers.userId, users.id))
    .where(eq(teamMembers.teamId, teamId));

  return { ...team, members };
}

// ─── createTeam ──────────────────────────────────────

export const createTeam = defineAction(
  createTeamSchema,
  async ({ name, description }): Promise<ActionResult<{ id: string }>> => {
    const user = await requireAuth();

    const [team] = await db
      .insert(teams)
      .values({
        name,
        description: description || null,
        ownerId: user.id,
      })
      .returning();

    // Add creator as admin member
    await db.insert(teamMembers).values({
      teamId: team.id,
      userId: user.id,
      role: "admin",
    });

    logger.action("team.create", user.id, { teamId: team.id });
    revalidatePath("/teams");

    return actionSuccess({ id: team.id });
  },
);

// ─── updateTeam ──────────────────────────────────────

export async function updateTeam(
  teamId: string,
  data: { name?: string; description?: string },
): Promise<ActionResult> {
  try {
    const user = await requireAuth();

    const [team] = await db.select().from(teams).where(eq(teams.id, teamId));
    if (!team) {
      return actionError(new AppError("团队不存在", "blocking", "NOT_FOUND", 404));
    }

    if (team.ownerId !== user.id) {
      // Check if user is admin member
      const [member] = await db
        .select()
        .from(teamMembers)
        .where(
          and(
            eq(teamMembers.teamId, teamId),
            eq(teamMembers.userId, user.id),
            eq(teamMembers.role, "admin"),
          ),
        );
      if (!member) {
        return actionError(new AppError("无权限修改团队", "blocking", "FORBIDDEN", 403));
      }
    }

    if (data.name !== undefined && !data.name.trim()) {
      return actionError(new AppError("团队名称不能为空", "blocking", "VALIDATION_ERROR"));
    }

    await db
      .update(teams)
      .set({
        ...(data.name !== undefined && { name: data.name.trim() }),
        ...(data.description !== undefined && {
          description: data.description?.trim() || null,
        }),
      })
      .where(eq(teams.id, teamId));

    logger.action("team.update", user.id, { teamId });
    revalidatePath("/teams");

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

// ─── deleteTeam ──────────────────────────────────────

export async function deleteTeam(teamId: string): Promise<ActionResult> {
  try {
    const user = await requireAuth();

    const [team] = await db.select().from(teams).where(eq(teams.id, teamId));
    if (!team) {
      return actionError(new AppError("团队不存在", "blocking", "NOT_FOUND", 404));
    }

    if (team.ownerId !== user.id) {
      return actionError(new AppError("只有团队创建者可以删除团队", "blocking", "FORBIDDEN", 403));
    }

    await db.delete(teams).where(eq(teams.id, teamId));

    logger.action("team.delete", user.id, { teamId });
    revalidatePath("/teams");

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

// ─── getTeamMembers ──────────────────────────────────

export async function getTeamMembers(teamId: string) {
  const user = await requireAuth();

  return db
    .select({
      id: teamMembers.id,
      userId: teamMembers.userId,
      role: teamMembers.role,
      joinedAt: teamMembers.joinedAt,
      userName: users.name,
      userEmail: users.email,
    })
    .from(teamMembers)
    .innerJoin(users, eq(teamMembers.userId, users.id))
    .where(eq(teamMembers.teamId, teamId));
}

// ─── inviteMember ────────────────────────────────────

export const inviteMember = defineAction(
  inviteMemberSchema,
  async ({ teamId, email, role: requestedRole }): Promise<ActionResult<{ memberId: string }>> => {
    const user = await requireAuth();

    const [team] = await db.select().from(teams).where(eq(teams.id, teamId));
    if (!team) {
      return actionError(new AppError("团队不存在", "blocking", ErrorCode.NOT_FOUND, 404));
    }

    // Only owner or admin can invite
    if (team.ownerId !== user.id) {
      const [member] = await db
        .select()
        .from(teamMembers)
        .where(
          and(
            eq(teamMembers.teamId, teamId),
            eq(teamMembers.userId, user.id),
            eq(teamMembers.role, "admin"),
          ),
        );
      if (!member) {
        return actionError(new AppError("无权限邀请成员", "blocking", ErrorCode.FORBIDDEN, 403));
      }
    }

    // Find user by email
    const [targetUser] = await db.select().from(users).where(eq(users.email, email));
    if (!targetUser) {
      return actionError(new AppError("该邮箱用户不存在", "blocking", ErrorCode.NOT_FOUND, 404));
    }

    // Check if already a member
    const [existing] = await db
      .select()
      .from(teamMembers)
      .where(and(eq(teamMembers.teamId, teamId), eq(teamMembers.userId, targetUser.id)));
    if (existing) {
      return actionError(
        new AppError("该用户已是团队成员", "blocking", ErrorCode.DUPLICATE_ENTRY, 409),
      );
    }

    const role = requestedRole;

    const [member] = await db
      .insert(teamMembers)
      .values({
        teamId,
        userId: targetUser.id,
        role,
      })
      .returning();

    logger.action("team.invite", user.id, {
      teamId,
      invitedUserId: targetUser.id,
    });
    revalidatePath("/teams");

    return actionSuccess({ memberId: member.id });
  },
);

// ─── removeMember ────────────────────────────────────

export async function removeMember(teamId: string, userId: string): Promise<ActionResult> {
  try {
    const user = await requireAuth();

    const [team] = await db.select().from(teams).where(eq(teams.id, teamId));
    if (!team) {
      return actionError(new AppError("团队不存在", "blocking", "NOT_FOUND", 404));
    }

    // Cannot remove owner
    if (userId === team.ownerId) {
      return actionError(new AppError("不能移除团队创建者", "blocking", "VALIDATION_ERROR"));
    }

    // Only owner or admin can remove
    if (team.ownerId !== user.id) {
      const [member] = await db
        .select()
        .from(teamMembers)
        .where(
          and(
            eq(teamMembers.teamId, teamId),
            eq(teamMembers.userId, user.id),
            eq(teamMembers.role, "admin"),
          ),
        );
      if (!member) {
        return actionError(new AppError("无权限移除成员", "blocking", "FORBIDDEN", 403));
      }
    }

    await db
      .delete(teamMembers)
      .where(and(eq(teamMembers.teamId, teamId), eq(teamMembers.userId, userId)));

    logger.action("team.removeMember", user.id, {
      teamId,
      removedUserId: userId,
    });
    revalidatePath("/teams");

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

// ─── updateMemberRole ────────────────────────────────

export async function updateMemberRole(
  teamId: string,
  userId: string,
  role: string,
): Promise<ActionResult> {
  try {
    const user = await requireAuth();

    const [team] = await db.select().from(teams).where(eq(teams.id, teamId));
    if (!team) {
      return actionError(new AppError("团队不存在", "blocking", "NOT_FOUND", 404));
    }

    if (team.ownerId !== user.id) {
      return actionError(new AppError("只有团队创建者可以修改角色", "blocking", "FORBIDDEN", 403));
    }

    if (userId === team.ownerId) {
      return actionError(new AppError("不能修改团队创建者的角色", "blocking", "VALIDATION_ERROR"));
    }

    const validRoles = ["admin", "member"];
    if (!validRoles.includes(role)) {
      return actionError(new AppError("无效的角色", "blocking", "VALIDATION_ERROR"));
    }

    await db
      .update(teamMembers)
      .set({ role })
      .where(and(eq(teamMembers.teamId, teamId), eq(teamMembers.userId, userId)));

    logger.action("team.updateRole", user.id, { teamId, targetUserId: userId, role });
    revalidatePath("/teams");

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

// ─── migrateProjectToTeam ────────────────────────────

export async function migrateProjectToTeam(
  projectId: string,
  teamId: string | null,
): Promise<ActionResult> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "admin");

    if (teamId) {
      const [team] = await db.select().from(teams).where(eq(teams.id, teamId));
      if (!team) {
        return actionError(new AppError("团队不存在", "blocking", "NOT_FOUND", 404));
      }

      // Verify user is member of the team
      const isMember =
        team.ownerId === user.id ||
        (
          await db
            .select()
            .from(teamMembers)
            .where(and(eq(teamMembers.teamId, teamId), eq(teamMembers.userId, user.id)))
        ).length > 0;

      if (!isMember) {
        return actionError(new AppError("你不是该团队成员", "blocking", "FORBIDDEN", 403));
      }
    }

    await db
      .update(projects)
      .set({ teamId, updatedAt: new Date() })
      .where(eq(projects.id, projectId));

    logger.action("project.migrateToTeam", user.id, { projectId, teamId });
    revalidatePath(`/projects/${projectId}`);

    return actionSuccess(undefined);
  } catch (error) {
    return actionError(error);
  }
}

// ─── getTeamProjects ─────────────────────────────────

export async function getTeamProjects(teamId: string) {
  const user = await requireAuth();

  return db.select().from(projects).where(eq(projects.teamId, teamId));
}
