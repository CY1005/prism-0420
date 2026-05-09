"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Bell, Plus, LogOut, Users, FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { getTeams, createTeam, getTeamMembers, getTeamProjects } from "@/actions/teams";
import { logout, getSessionUser } from "@/actions/auth";

type TeamSummary = {
  id: string;
  name: string;
  description: string | null;
  ownerId: string;
  createdAt: Date;
  memberCount: number;
  projectCount: number;
};

export default function TeamsPage() {
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [userName, setUserName] = useState("");
  const [userInitials, setUserInitials] = useState("");
  const [createDialog, setCreateDialog] = useState(false);
  const [newTeamName, setNewTeamName] = useState("");
  const [newTeamDesc, setNewTeamDesc] = useState("");
  const [creating, setCreating] = useState(false);

  const loadTeams = async () => {
    const rawTeams = await getTeams();
    const summaries: TeamSummary[] = await Promise.all(
      rawTeams.map(async (t) => {
        const members = await getTeamMembers(t.id);
        const projects = await getTeamProjects(t.id);
        return {
          ...t,
          memberCount: members.length,
          projectCount: projects.length,
        };
      }),
    );
    setTeams(summaries);
  };

  useEffect(() => {
    loadTeams();
    getSessionUser().then((user) => {
      if (user) {
        setUserName(user.name);
        setUserInitials(user.name.charAt(0));
      }
    });
  }, []);

  const handleCreate = async () => {
    if (!newTeamName.trim()) return;
    setCreating(true);
    const result = await createTeam({
      name: newTeamName.trim(),
      description: newTeamDesc.trim() || undefined,
    });
    if (result.success) {
      setCreateDialog(false);
      setNewTeamName("");
      setNewTeamDesc("");
      await loadTeams();
    }
    setCreating(false);
  };

  const handleLogout = async () => {
    await logout();
  };

  return (
    <div className="bg-background flex min-h-screen flex-col">
      <header className="border-border bg-card flex h-14 items-center justify-between border-b px-6">
        <Link
          href="/projects"
          className="text-foreground hover:text-primary text-lg font-semibold transition-colors"
        >
          Prism
        </Link>
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <Bell className="text-muted-foreground h-4 w-4" />
          </Button>
          <div className="flex items-center gap-2">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-muted text-sm">{userInitials || "?"}</AvatarFallback>
            </Avatar>
            <span className="text-foreground text-sm">{userName}</span>
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleLogout}>
            <LogOut className="text-muted-foreground h-4 w-4" />
          </Button>
        </div>
      </header>

      <div className="flex items-center justify-between px-6 py-4">
        <h1 className="text-foreground text-xl font-semibold">团队空间</h1>
        <Button variant="default" onClick={() => setCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          创建团队
        </Button>
      </div>

      {teams.length === 0 ? (
        <div className="flex flex-col items-center justify-center px-6 py-16">
          <Users className="text-muted-foreground/40 mb-4 h-12 w-12" />
          <h3 className="mb-2 text-lg font-semibold">还没有团队</h3>
          <p className="text-muted-foreground mb-4 text-sm">创建一个团队来协作管理项目</p>
          <Button variant="default" onClick={() => setCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            创建团队
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 px-6">
          {teams.map((team) => (
            <Link key={team.id} href={`/teams/${team.id}`}>
              <Card className="border-border/60 hover:border-primary/40 cursor-pointer p-5 shadow-sm transition-all hover:shadow-md">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-foreground font-semibold">{team.name}</h3>
                    {team.description && (
                      <p className="text-muted-foreground mt-1 text-sm">{team.description}</p>
                    )}
                  </div>
                </div>
                <div className="mt-3 flex gap-6">
                  <div className="flex items-center gap-1.5">
                    <Users className="text-muted-foreground h-4 w-4" />
                    <span className="text-foreground text-2xl font-bold">{team.memberCount}</span>
                    <span className="text-muted-foreground text-xs">成员</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <FolderOpen className="text-muted-foreground h-4 w-4" />
                    <span className="text-foreground text-2xl font-bold">{team.projectCount}</span>
                    <span className="text-muted-foreground text-xs">项目</span>
                  </div>
                </div>
                <div className="mt-4">
                  <span className="text-muted-foreground text-xs">
                    创建于 {new Date(team.createdAt).toLocaleDateString("zh-CN")}
                  </span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {/* Create Team Dialog */}
      <Dialog open={createDialog} onOpenChange={setCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>创建团队</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>团队名称</Label>
              <Input
                value={newTeamName}
                onChange={(e) => setNewTeamName(e.target.value)}
                placeholder="输入团队名称"
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label>团队描述</Label>
              <Input
                value={newTeamDesc}
                onChange={(e) => setNewTeamDesc(e.target.value)}
                placeholder="可选，简要描述团队职责"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialog(false)}>
              取消
            </Button>
            <Button onClick={handleCreate} disabled={!newTeamName.trim() || creating}>
              {creating ? "创建中..." : "创建"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
