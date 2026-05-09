"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bell, Plus, LogOut, Shield, Users } from "lucide-react";
import { GlobalSearchBar } from "@/components/global-search-bar";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { projectsStrings } from "@/lib/projects-data";
import { cn } from "@/lib/utils";
import { useState, useEffect } from "react";
import { getProjects } from "@/actions/projects";
import { useAuth } from "@/contexts/auth-context";
import { isNextRedirectError } from "@/lib/errors";
import type { components } from "@/types/api";

type ProjectResponse = components["schemas"]["ProjectResponse"];

const typeColorMap: Record<string, string> = {
  blue: "border-blue-200 text-blue-700 bg-blue-50",
  green: "border-green-200 text-green-700 bg-green-50",
  purple: "border-purple-200 text-purple-700 bg-purple-50",
  orange: "border-orange-200 text-orange-700 bg-orange-50",
};

const templateLabel: Record<string, string> = {
  product_analysis: "产品分析",
  system_architecture: "系统架构",
  research_platform: "研究平台",
  custom: "自定义",
};

const templateColor: Record<string, string> = {
  product_analysis: "blue",
  system_architecture: "green",
  research_platform: "purple",
  custom: "orange",
};

type ProjectTab = "personal" | "team";

export default function ProjectsPage() {
  const router = useRouter();
  const { user, isLoading, logout } = useAuth();
  const [apiProjects, setApiProjects] = useState<ProjectResponse[] | null>(null);
  const [activeTab, setActiveTab] = useState<ProjectTab>("personal");

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    getProjects()
      .then((projects) => setApiProjects(projects))
      .catch((error) => {
        if (isNextRedirectError(error)) throw error;
        setApiProjects([]);
      });
  }, [user, isLoading, router]);

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  const userName = user?.name ?? "";
  const userInitials = user?.name?.charAt(0) ?? "?";

  const displayProjects = (apiProjects ?? []).map((p) => ({
    id: p.id,
    title: p.name,
    type: templateLabel[p.template_type] || p.template_type,
    typeColor: templateColor[p.template_type] || "blue",
    description: p.description || "",
    stats: [
      { value: 0, label: "模块" },
      { value: 0, label: "功能项" },
      { value: "0%", label: "完善度" },
    ],
    lastUpdated: new Date(p.created_at).toLocaleDateString("zh-CN"),
    members: [userInitials],
  }));

  return (
    <div className="bg-background flex min-h-screen flex-col">
      <header className="border-border bg-card flex h-14 items-center justify-between border-b px-6">
        <Link
          href="/projects"
          className="text-foreground hover:text-primary text-lg font-semibold transition-colors"
        >
          Prism
        </Link>
        <GlobalSearchBar />
        <div className="flex items-center gap-4">
          <Link href="/admin">
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <Shield className="text-muted-foreground h-4 w-4" />
            </Button>
          </Link>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <Bell className="text-muted-foreground h-4 w-4" />
          </Button>
          <div className="flex items-center gap-2">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-muted text-sm">{userInitials}</AvatarFallback>
            </Avatar>
            <span className="text-foreground text-sm">{userName}</span>
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleLogout}>
            <LogOut className="text-muted-foreground h-4 w-4" />
          </Button>
        </div>
      </header>

      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-4">
          <div className="bg-muted/30 flex items-center gap-1 rounded-lg border p-1">
            <button
              onClick={() => setActiveTab("personal")}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                activeTab === "personal"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              我的项目
            </button>
            <button
              onClick={() => setActiveTab("team")}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                activeTab === "team"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Users className="h-3.5 w-3.5" />
              团队项目
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/teams">
            <Button variant="outline">
              <Users className="mr-2 h-4 w-4" />
              团队空间
            </Button>
          </Link>
          <Link href="/projects/new">
            <Button variant="default">
              <Plus className="mr-2 h-4 w-4" />
              {projectsStrings.newProject}
            </Button>
          </Link>
        </div>
      </div>

      {activeTab === "personal" && (
        <div className="grid grid-cols-2 gap-4 px-6">
          {displayProjects.map((project) => (
            <Link key={project.id} href={`/projects/${project.id}`}>
              <Card className="border-border/60 hover:border-primary/40 cursor-pointer p-5 shadow-sm transition-all hover:shadow-md">
                <div className="flex items-start justify-between">
                  <div>
                    <Badge
                      variant="outline"
                      className={cn("mb-2 text-xs", typeColorMap[project.typeColor])}
                    >
                      {project.type}
                    </Badge>
                    <h3 className="text-foreground font-semibold">{project.title}</h3>
                  </div>
                </div>
                <p className="text-muted-foreground mt-1 text-sm">{project.description}</p>
                <div className="mt-3 flex gap-4">
                  {project.stats.map((stat, index) => (
                    <div key={index}>
                      <span
                        className={cn(
                          "text-2xl font-bold",
                          index === project.stats.length - 1 ? "text-primary" : "text-foreground",
                        )}
                      >
                        {stat.value}
                      </span>
                      <p className="text-muted-foreground text-xs">{stat.label}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-muted-foreground text-xs">
                    {projectsStrings.lastUpdated}
                    {project.lastUpdated}
                  </span>
                  <div className="flex">
                    {project.members.map((member, index) => (
                      <Avatar
                        key={index}
                        className={`border-card h-6 w-6 border-2 ${index > 0 ? "-ml-2" : ""}`}
                      >
                        <AvatarFallback className="bg-muted text-xs">{member}</AvatarFallback>
                      </Avatar>
                    ))}
                  </div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {activeTab === "team" && (
        <div className="space-y-6 px-6">
          <div className="flex flex-col items-center justify-center py-16">
            <Users className="text-muted-foreground/40 mb-4 h-12 w-12" />
            <h3 className="mb-2 text-lg font-semibold">团队项目（subslice 4 启用）</h3>
            <p className="text-muted-foreground mb-4 text-sm">
              M20 团队页前端在 Phase 2.2 子片 4 接通。当前显示个人项目。
            </p>
            <Link href="/teams">
              <Button variant="outline">
                <Users className="mr-2 h-4 w-4" />
                前往团队空间
              </Button>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
