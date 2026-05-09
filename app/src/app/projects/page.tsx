"use client";

import Link from "next/link";
import { Bell, Plus, LogOut, Shield, Users } from "lucide-react";
import { GlobalSearchBar } from "@/components/global-search-bar";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { projectsData, projectsStrings } from "@/lib/projects-data";
import { cn } from "@/lib/utils";
import { useState, useEffect } from "react";
import { getProjects } from "@/actions/projects";
import { logout, getSessionUser } from "@/actions/auth";
import { getTeams, getTeamProjects } from "@/actions/teams";

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

type TeamGroup = {
  teamId: string;
  teamName: string;
  projects: {
    id: string;
    name: string;
    description: string | null;
    templateType: string;
    createdAt: Date;
  }[];
};

export default function ProjectsPage() {
  const [apiProjects, setApiProjects] = useState<Awaited<ReturnType<typeof getProjects>> | null>(
    null,
  );
  const [userName, setUserName] = useState("");
  const [userInitials, setUserInitials] = useState("");
  const [activeTab, setActiveTab] = useState<ProjectTab>("personal");
  const [teamGroups, setTeamGroups] = useState<TeamGroup[]>([]);

  useEffect(() => {
    getProjects()
      .then((projects) => {
        setApiProjects(projects);
      })
      .catch(() => setApiProjects([]));
    getSessionUser().then((user) => {
      if (user) {
        setUserName(user.name);
        setUserInitials(user.name.charAt(0));
      }
    });
    // Load team projects
    getTeams().then(async (teams) => {
      const groups: TeamGroup[] = await Promise.all(
        teams.map(async (t) => {
          const projs = await getTeamProjects(t.id);
          return {
            teamId: t.id,
            teamName: t.name,
            projects: projs as TeamGroup["projects"],
          };
        }),
      );
      setTeamGroups(groups.filter((g) => g.projects.length > 0));
    });
  }, []);

  const handleLogout = async () => {
    await logout();
  };

  // Use API data if available, otherwise mock
  const displayProjects = apiProjects
    ? apiProjects.map((p) => ({
        id: p.id,
        title: p.name,
        type: templateLabel[p.templateType] || p.templateType,
        typeColor: templateColor[p.templateType] || "blue",
        description: p.description || "",
        stats: [
          { value: p.nodeCount, label: "模块" },
          { value: 0, label: "功能项" },
          { value: "0%", label: "完善度" },
        ],
        lastUpdated: p.createdAt ? new Date(p.createdAt).toLocaleDateString("zh-CN") : "",
        members: ["CY"],
      }))
    : [];

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
          {teamGroups.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <Users className="text-muted-foreground/40 mb-4 h-12 w-12" />
              <h3 className="mb-2 text-lg font-semibold">暂无团队项目</h3>
              <p className="text-muted-foreground mb-4 text-sm">
                在项目设置中将项目迁移到团队，或前往团队空间创建团队
              </p>
              <Link href="/teams">
                <Button variant="outline">
                  <Users className="mr-2 h-4 w-4" />
                  前往团队空间
                </Button>
              </Link>
            </div>
          ) : (
            teamGroups.map((group) => (
              <div key={group.teamId}>
                <div className="mb-3 flex items-center gap-2">
                  <Users className="text-muted-foreground h-4 w-4" />
                  <h2 className="text-base font-semibold">{group.teamName}</h2>
                  <Badge variant="secondary" className="text-xs">
                    {group.projects.length} 个项目
                  </Badge>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  {group.projects.map((project) => (
                    <Link key={project.id} href={`/projects/${project.id}`}>
                      <Card className="border-border/60 hover:border-primary/40 cursor-pointer p-5 shadow-sm transition-all hover:shadow-md">
                        <div className="flex items-start justify-between">
                          <div>
                            <Badge
                              variant="outline"
                              className={cn(
                                "mb-2 text-xs",
                                typeColorMap[templateColor[project.templateType] || "blue"],
                              )}
                            >
                              {templateLabel[project.templateType] || project.templateType}
                            </Badge>
                            <h3 className="text-foreground font-semibold">{project.name}</h3>
                          </div>
                        </div>
                        {project.description && (
                          <p className="text-muted-foreground mt-1 text-sm">
                            {project.description}
                          </p>
                        )}
                        <div className="mt-4">
                          <span className="text-muted-foreground text-xs">
                            创建于 {new Date(project.createdAt).toLocaleDateString("zh-CN")}
                          </span>
                        </div>
                      </Card>
                    </Link>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
