"use client";

import { useEffect, useState, useTransition, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Users, Trash2, AlertTriangle, UserPlus, Crown, Edit3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/contexts/auth-context";
import {
  getTeam,
  updateTeam,
  deleteTeam,
  transferOwnership,
  addMember,
  removeMember,
} from "@/actions/teams";
import { handleActionResult } from "@/lib/client-error";
import { isNextRedirectError } from "@/lib/errors";
import type { components } from "@/types/api";

type TeamRead = components["schemas"]["TeamRead"];

export default function TeamDetailPage({ params }: { params: Promise<{ teamId: string }> }) {
  const router = useRouter();
  const { teamId } = use(params);
  const { user, isLoading } = useAuth();
  const [team, setTeam] = useState<TeamRead | null>(null);
  const [loadError, setLoadError] = useState(false);

  const reload = () => {
    getTeam(teamId)
      .then((t) => {
        if (!t) setLoadError(true);
        else setTeam(t);
      })
      .catch((error) => {
        if (isNextRedirectError(error)) throw error;
        setLoadError(true);
      });
  };

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, isLoading, teamId, router]);

  if (loadError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <Card className="max-w-md p-8 text-center">
          <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-red-400" />
          <p className="mb-4 text-slate-700">团队不存在或你无权访问</p>
          <Link href="/teams">
            <Button variant="outline">返回团队列表</Button>
          </Link>
        </Card>
      </div>
    );
  }

  if (!team) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-slate-500">加载中…</p>
      </div>
    );
  }

  const isOwner = user?.id === team.creator_id;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 max-w-5xl items-center gap-4 px-6">
          <Link href="/teams">
            <Button variant="ghost" size="sm" className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              返回
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-slate-500" />
            <h1 className="text-lg font-semibold text-slate-900">{team.name}</h1>
            {isOwner && (
              <span className="inline-flex items-center gap-1 rounded bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                <Crown className="h-3 w-3" />
                Owner
              </span>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-6 py-8">
        <TeamInfoCard team={team} />
        <TeamEditCard team={team} canEdit={isOwner} onUpdated={reload} />
        <TeamMembersCard team={team} canManage={isOwner} onChanged={reload} />
        {isOwner && <TeamTransferCard team={team} onTransferred={reload} />}
        {isOwner && <TeamDangerCard team={team} />}
      </main>
    </div>
  );
}

// ─── Info ───────────────────────────────────────────

function TeamInfoCard({ team }: { team: TeamRead }) {
  return (
    <Card className="p-6">
      <h2 className="mb-4 text-base font-semibold text-slate-900">基本信息</h2>
      <dl className="grid grid-cols-1 gap-4 text-sm md:grid-cols-2">
        <div>
          <dt className="mb-1 text-slate-500">团队名称</dt>
          <dd className="text-slate-900">{team.name}</dd>
        </div>
        <div>
          <dt className="mb-1 text-slate-500">成员数</dt>
          <dd className="text-slate-900">{team.member_count}</dd>
        </div>
        <div className="md:col-span-2">
          <dt className="mb-1 text-slate-500">描述</dt>
          <dd className="whitespace-pre-wrap text-slate-900">{team.description || "（无描述）"}</dd>
        </div>
        <div>
          <dt className="mb-1 text-slate-500">创建于</dt>
          <dd className="text-slate-900">{new Date(team.created_at).toLocaleString("zh-CN")}</dd>
        </div>
        <div>
          <dt className="mb-1 text-slate-500">最近更新</dt>
          <dd className="text-slate-900">{new Date(team.updated_at).toLocaleString("zh-CN")}</dd>
        </div>
      </dl>
    </Card>
  );
}

// ─── Edit ───────────────────────────────────────────

function TeamEditCard({
  team,
  canEdit,
  onUpdated,
}: {
  team: TeamRead;
  canEdit: boolean;
  onUpdated: () => void;
}) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(team.name);
  const [description, setDescription] = useState(team.description ?? "");
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  const submit = () => {
    setError("");
    startTransition(async () => {
      const result = await updateTeam(team.id, {
        name: name.trim() !== team.name ? name.trim() : undefined,
        description:
          description.trim() !== (team.description ?? "") ? description.trim() : undefined,
        version: team.version,
      });
      const handled = handleActionResult(result, router);
      if (handled.ok) {
        setEditing(false);
        onUpdated();
      } else if (!handled.autoHandled) {
        setError(handled.message);
      }
    });
  };

  return (
    <Card className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-900">编辑团队</h2>
        {canEdit && !editing && (
          <Button variant="outline" size="sm" className="gap-2" onClick={() => setEditing(true)}>
            <Edit3 className="h-3.5 w-3.5" />
            编辑
          </Button>
        )}
      </div>
      {!canEdit ? (
        <p className="text-sm text-slate-500">
          仅团队 owner 可编辑（admin 编辑权限待 Phase 2.3 启用）
        </p>
      ) : !editing ? (
        <p className="text-sm text-slate-500">点击右上角「编辑」修改团队名称或描述</p>
      ) : (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="edit-name">团队名称</Label>
            <Input
              id="edit-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
              disabled={isPending}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit-desc">描述</Label>
            <Textarea
              id="edit-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={500}
              rows={3}
              disabled={isPending}
            />
          </div>
          {error && (
            <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
              {error}
            </div>
          )}
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setEditing(false);
                setName(team.name);
                setDescription(team.description ?? "");
                setError("");
              }}
              disabled={isPending}
            >
              取消
            </Button>
            <Button onClick={submit} disabled={isPending || !name.trim()}>
              {isPending ? "保存中…" : "保存"}
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}

// ─── Members ────────────────────────────────────────

function TeamMembersCard({
  team,
  canManage,
  onChanged,
}: {
  team: TeamRead;
  canManage: boolean;
  onChanged: () => void;
}) {
  const router = useRouter();
  const [addOpen, setAddOpen] = useState(false);
  const [removeOpen, setRemoveOpen] = useState(false);
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState<"admin" | "member">("member");
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  const submitAdd = () => {
    setError("");
    startTransition(async () => {
      const result = await addMember(team.id, userId.trim(), role);
      const handled = handleActionResult(result, router);
      if (handled.ok) {
        setAddOpen(false);
        setUserId("");
        setRole("member");
        onChanged();
      } else if (!handled.autoHandled) {
        setError(handled.message);
      }
    });
  };

  const submitRemove = () => {
    setError("");
    startTransition(async () => {
      const result = await removeMember(team.id, userId.trim());
      const handled = handleActionResult(result, router);
      if (handled.ok) {
        setRemoveOpen(false);
        setUserId("");
        const residual = handled.data?.residual_count ?? 0;
        if (residual > 0) {
          alert(
            `已从团队移除。该用户在 ${residual} 个项目中仍保留独立成员身份（M20 design Q3=A 软切断）。`,
          );
        }
        onChanged();
      } else if (!handled.autoHandled) {
        setError(handled.message);
      }
    });
  };

  return (
    <Card className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-900">成员管理</h2>
        {canManage && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => {
                setError("");
                setAddOpen(true);
              }}
            >
              <UserPlus className="h-3.5 w-3.5" />
              添加成员
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setError("");
                setRemoveOpen(true);
              }}
            >
              移除成员
            </Button>
          </div>
        )}
      </div>

      <div className="rounded border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        <p className="mb-1 font-medium">当前共 {team.member_count} 名成员</p>
        <p className="text-slate-500">
          成员名单展示等 backend 上线{" "}
          <code className="rounded bg-white px-1 text-xs">GET /api/teams/{"{id}"}/members</code>{" "}
          endpoint 后启用（cross-sprint pool P22-4-backend-gap / Phase 2.3）。
          {canManage && " 管理操作可按用户 ID 直接进行。"}
        </p>
      </div>

      {/* Add member dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加成员</DialogTitle>
            <DialogDescription>
              按用户 ID 添加成员（用户检索功能待 Phase 2.3 启用）。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="add-user-id">用户 ID（UUID）</Label>
              <Input
                id="add-user-id"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="00000000-0000-0000-0000-000000000000"
                disabled={isPending}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="add-role">角色</Label>
              <Select
                value={role}
                onValueChange={(v) => setRole(v as "admin" | "member")}
                disabled={isPending}
              >
                <SelectTrigger id="add-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="member">member</SelectItem>
                  <SelectItem value="admin">admin</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {error && (
              <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
                {error}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)} disabled={isPending}>
              取消
            </Button>
            <Button onClick={submitAdd} disabled={isPending || !userId.trim()}>
              {isPending ? "添加中…" : "添加"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Remove member dialog */}
      <Dialog open={removeOpen} onOpenChange={setRemoveOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>移除成员</DialogTitle>
            <DialogDescription>
              按用户 ID 移除成员。该用户在 project 中的独立 ProjectMember 不会被自动清理（M20 Q3=A
              软切断）。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="rm-user-id">用户 ID（UUID）</Label>
              <Input
                id="rm-user-id"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="00000000-0000-0000-0000-000000000000"
                disabled={isPending}
              />
            </div>
            {error && (
              <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
                {error}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoveOpen(false)} disabled={isPending}>
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={submitRemove}
              disabled={isPending || !userId.trim()}
            >
              {isPending ? "移除中…" : "确认移除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

// ─── Transfer ───────────────────────────────────────

function TeamTransferCard({ team, onTransferred }: { team: TeamRead; onTransferred: () => void }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [newOwnerId, setNewOwnerId] = useState("");
  const [confirmText, setConfirmText] = useState("");
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  const submit = () => {
    setError("");
    startTransition(async () => {
      const result = await transferOwnership(team.id, newOwnerId.trim());
      const handled = handleActionResult(result, router);
      if (handled.ok) {
        setOpen(false);
        setNewOwnerId("");
        setConfirmText("");
        onTransferred();
      } else if (!handled.autoHandled) {
        setError(handled.message);
      }
    });
  };

  return (
    <Card className="border-amber-200 p-6">
      <h2 className="mb-2 text-base font-semibold text-slate-900">转让所有权</h2>
      <p className="mb-4 text-sm text-slate-500">
        将团队 owner 转让给另一名成员；原 owner 自动降为 admin。目标用户必须已是该团队的 admin 或
        member。
      </p>
      <Button
        variant="outline"
        onClick={() => {
          setError("");
          setOpen(true);
        }}
      >
        转让所有权
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>转让所有权</DialogTitle>
            <DialogDescription>
              转让后你将自动降为 admin，无法直接撤回。请输入目标用户 ID 并在下方输入团队名{" "}
              <strong>{team.name}</strong> 确认。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="new-owner-id">新 owner 用户 ID（UUID）</Label>
              <Input
                id="new-owner-id"
                value={newOwnerId}
                onChange={(e) => setNewOwnerId(e.target.value)}
                placeholder="00000000-0000-0000-0000-000000000000"
                disabled={isPending}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="transfer-confirm">输入 &quot;{team.name}&quot; 确认</Label>
              <Input
                id="transfer-confirm"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                disabled={isPending}
              />
            </div>
            {error && (
              <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
                {error}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={isPending}>
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={submit}
              disabled={isPending || !newOwnerId.trim() || confirmText !== team.name}
            >
              {isPending ? "转让中…" : "确认转让"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

// ─── Danger ─────────────────────────────────────────

function TeamDangerCard({ team }: { team: TeamRead }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  const submit = () => {
    setError("");
    startTransition(async () => {
      const result = await deleteTeam(team.id);
      const handled = handleActionResult(result, router);
      if (handled.ok) {
        router.replace("/teams");
      } else if (!handled.autoHandled) {
        setError(handled.message);
      }
    });
  };

  return (
    <Card className="border-red-200 p-6">
      <h2 className="mb-2 flex items-center gap-2 text-base font-semibold text-red-700">
        <AlertTriangle className="h-4 w-4" />
        危险操作
      </h2>
      <p className="mb-1 text-sm text-slate-600">
        删除团队不可撤销（hard delete / M20 design §3 Q8=B）。
      </p>
      <p className="mb-4 text-sm text-slate-500">
        删除前必须先迁出所有归属该团队的项目，否则后端会返回{" "}
        <code className="rounded bg-slate-100 px-1 text-xs">TEAM_HAS_PROJECTS</code> 错误。
      </p>
      <Button
        variant="destructive"
        className="gap-2"
        onClick={() => {
          setError("");
          setOpen(true);
        }}
      >
        <Trash2 className="h-4 w-4" />
        删除团队
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-700">永久删除团队</DialogTitle>
            <DialogDescription>
              此操作不可撤销。请输入团队名 <strong>{team.name}</strong> 确认。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="delete-confirm">输入 &quot;{team.name}&quot; 确认</Label>
              <Input
                id="delete-confirm"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                disabled={isPending}
              />
            </div>
            {error && (
              <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
                {error}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={isPending}>
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={submit}
              disabled={isPending || confirmText !== team.name}
            >
              {isPending ? "删除中…" : "永久删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
