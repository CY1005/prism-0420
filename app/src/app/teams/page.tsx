"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus, Users, Bell, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useAuth } from "@/contexts/auth-context";
import { getTeams } from "@/actions/teams";
import { isNextRedirectError } from "@/lib/errors";
import type { components } from "@/types/api";

type TeamRead = components["schemas"]["TeamRead"];

export default function TeamsPage() {
  const router = useRouter();
  const { user, isLoading, logout } = useAuth();
  const [teams, setTeams] = useState<TeamRead[] | null>(null);

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    getTeams()
      .then(setTeams)
      .catch((error) => {
        if (isNextRedirectError(error)) throw error;
        setTeams([]);
      });
  }, [user, isLoading, router]);

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  const userInitials = user?.name?.charAt(0) ?? "?";

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-4">
            <Link href="/projects" className="text-lg font-semibold text-slate-900">
              Prism
            </Link>
            <nav className="ml-4 flex items-center gap-1">
              <Link href="/projects">
                <Button variant="ghost" size="sm">
                  项目
                </Button>
              </Link>
              <Button variant="secondary" size="sm" className="gap-2">
                <Users className="h-4 w-4" />
                团队
              </Button>
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon">
              <Bell className="h-5 w-5" />
            </Button>
            <Avatar className="h-8 w-8">
              <AvatarFallback>{userInitials}</AvatarFallback>
            </Avatar>
            <Button variant="ghost" size="icon" onClick={handleLogout}>
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">我的团队</h1>
            <p className="mt-1 text-sm text-slate-500">
              团队是项目的容器；成员可共同访问团队内的所有项目
            </p>
          </div>
          <Link href="/teams/new">
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              新建团队
            </Button>
          </Link>
        </div>

        {teams === null ? (
          <Card className="p-8 text-center text-slate-500">加载中…</Card>
        ) : teams.length === 0 ? (
          <Card className="p-12 text-center">
            <Users className="mx-auto mb-4 h-12 w-12 text-slate-300" />
            <p className="mb-2 text-slate-600">你还没有加入任何团队</p>
            <p className="mb-6 text-sm text-slate-400">创建一个团队来邀请成员共同协作</p>
            <Link href="/teams/new">
              <Button>新建团队</Button>
            </Link>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {teams.map((team) => (
              <Link key={team.id} href={`/teams/${team.id}`}>
                <Card className="h-full cursor-pointer p-5 transition-shadow hover:shadow-md">
                  <div className="mb-3 flex items-start justify-between">
                    <h3 className="line-clamp-1 font-semibold text-slate-900">{team.name}</h3>
                    {team.creator_id === user?.id && (
                      <span className="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                        我创建的
                      </span>
                    )}
                  </div>
                  <p className="mb-4 line-clamp-2 min-h-[2.5rem] text-sm text-slate-500">
                    {team.description || "（无描述）"}
                  </p>
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="flex items-center gap-1">
                      <Users className="h-3.5 w-3.5" />
                      {team.member_count} 名成员
                    </span>
                    <span>{new Date(team.created_at).toLocaleDateString("zh-CN")}</span>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
