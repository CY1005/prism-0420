"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { use } from "react";
import {
  Bell,
  UserPlus,
  LogOut,
  GripVertical,
  Folder,
  File,
  Download,
  ArrowRightLeft,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ChevronRight } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import {
  getProject,
  updateProject,
  getProjectMembers,
  addProjectMember,
  removeProjectMember,
  updateProjectAIConfig,
} from "@/actions/projects";
import {
  getProjectDimensionConfigs,
  updateDimensionConfig,
  type DimensionConfigRow,
} from "@/actions/project-settings";
import { useAuth } from "@/contexts/auth-context";
import { useProjectRole } from "@/contexts/project-role-context";
import {
  getCompetitorsByProject,
  createCompetitor,
  updateCompetitor,
  deleteCompetitor,
} from "@/actions/competitors";
import {
  getFeedSources,
  createFeedSource,
  updateFeedSource,
  deleteFeedSource,
} from "@/actions/feed";
import { CompetitorManagement, type Competitor } from "@/components/competitor-reference-card";
import { Rss, Eye, EyeOff, Trash2, Plus } from "lucide-react";
import { exportProject } from "@/actions/export";
import { getTeams, moveProjectTeam } from "@/actions/teams";

type TabType =
  | "basic"
  | "dimensions"
  | "hierarchy"
  | "members"
  | "ai"
  | "competitors"
  | "feed-sources"
  | "export"
  | "team";

type ProjectData = {
  id: string;
  name: string;
  description: string | null;
  templateType: string;
  hierarchyLabels: string[];
  versionMode: string;
  aiProvider: string | null;
  aiApiKeyEnc: string | null;
};

type MemberData = {
  id: string;
  userId: string;
  role: string;
  createdAt: Date;
  userName: string;
  userEmail: string;
};

const ROLE_BADGE: Record<string, { label: string; variant: string }> = {
  admin: { label: "管理员", variant: "default" },
  editor: { label: "编辑者", variant: "green" },
  viewer: { label: "查看者", variant: "secondary" },
};

export default function ProjectSettingsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const { canAdmin } = useProjectRole();
  const [activeTab, setActiveTab] = useState<TabType>("dimensions");
  const [project, setProject] = useState<ProjectData | null>(null);
  const [members, setMembers] = useState<MemberData[]>([]);
  const [dimensionConfigs, setDimensionConfigs] = useState<DimensionConfigRow[]>([]);
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [level1, setLevel1] = useState("产品线");
  const [level2, setLevel2] = useState("模块");
  const [level3, setLevel3] = useState("功能项");
  const [aiProvider, setAiProvider] = useState("local");
  const [aiApiKey, setAiApiKey] = useState("");
  const [aiKeyConfigured, setAiKeyConfigured] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("viewer");
  const [saving, setSaving] = useState(false);
  const { user, logout } = useAuth();
  const userName = user?.name ?? "";
  const userInitials = user?.name?.charAt(0) ?? "";
  const [competitorsList, setCompetitorsList] = useState<Competitor[]>([]);
  const [feedSourcesList, setFeedSourcesList] = useState<
    {
      id: string;
      name: string;
      url: string;
      sourceType: string;
      isActive: boolean;
      createdAt: Date;
    }[]
  >([]);
  const [newFeedName, setNewFeedName] = useState("");
  const [newFeedUrl, setNewFeedUrl] = useState("");
  const [newFeedType, setNewFeedType] = useState("rss");
  // F19: Export
  const [exporting, setExporting] = useState(false);
  // F20: Teams
  const [teamsList, setTeamsList] = useState<
    { id: string; name: string; description: string | null }[]
  >([]);
  const [selectedTeamId, setSelectedTeamId] = useState<string>("");
  const [migrating, setMigrating] = useState(false);
  const [migrateConfirmDialog, setMigrateConfirmDialog] = useState(false);

  useEffect(() => {
    getProject(projectId).then((p) => {
      if (p) {
        setProject(p as ProjectData);
        setProjectName(p.name);
        setProjectDescription(p.description || "");
        const labels = p.hierarchyLabels as string[];
        if (labels?.length >= 3) {
          setLevel1(labels[0]);
          setLevel2(labels[1]);
          setLevel3(labels[2]);
        }
        setAiProvider(p.aiProvider || "local");
        setAiKeyConfigured(!!p.aiApiKeyEnc);
      }
    });
    loadMembers();
    loadDimensions();
    loadCompetitors();
    loadFeedSourcesList();
    getTeams().then((t) => setTeamsList(t as typeof teamsList));
  }, [projectId]);

  const loadMembers = async () => {
    try {
      const m = await getProjectMembers(projectId);
      setMembers(m as MemberData[]);
    } catch {
      // ignore
    }
  };

  const loadDimensions = async () => {
    try {
      const configs = await getProjectDimensionConfigs(projectId);
      setDimensionConfigs(configs);
    } catch {
      // ignore
    }
  };

  const loadCompetitors = async () => {
    try {
      const comps = await getCompetitorsByProject(projectId);
      setCompetitorsList(comps as Competitor[]);
    } catch {
      // ignore
    }
  };

  const loadFeedSourcesList = async () => {
    try {
      const sources = await getFeedSources(projectId);
      setFeedSourcesList(sources as typeof feedSourcesList);
    } catch {
      // ignore
    }
  };

  const handleCreateFeedSource = async () => {
    if (!newFeedName.trim() || !newFeedUrl.trim()) return;
    await createFeedSource(projectId, {
      name: newFeedName.trim(),
      url: newFeedUrl.trim(),
      sourceType: newFeedType,
    });
    setNewFeedName("");
    setNewFeedUrl("");
    await loadFeedSourcesList();
  };

  const handleToggleFeedSource = async (sourceId: string, isActive: boolean) => {
    await updateFeedSource(sourceId, { isActive });
    await loadFeedSourcesList();
  };

  const handleDeleteFeedSource = async (sourceId: string) => {
    await deleteFeedSource(sourceId);
    await loadFeedSourcesList();
  };

  const handleCreateCompetitor = async (data: {
    name: string;
    website?: string;
    description?: string;
  }) => {
    const result = await createCompetitor({ projectId, ...data });
    if (result.success) await loadCompetitors();
  };

  const handleUpdateCompetitor = async (
    id: string,
    data: { name?: string; website?: string; description?: string },
  ) => {
    const result = await updateCompetitor(id, data);
    if (result.success) await loadCompetitors();
  };

  const handleDeleteCompetitor = async (id: string) => {
    const result = await deleteCompetitor(id);
    if (result.success) await loadCompetitors();
  };

  const handleToggleDimension = (configId: number, enabled: boolean) => {
    setDimensionConfigs((prev) =>
      prev.map((c) => (c.configId === configId ? { ...c, enabled } : c)),
    );
  };

  const handleSaveDimensions = async () => {
    setSaving(true);
    await updateDimensionConfig(
      projectId,
      dimensionConfigs.map((c, i) => ({
        dimensionTypeId: c.dimensionTypeId,
        enabled: c.enabled,
        sortOrder: i,
      })),
    );
    setSaving(false);
  };

  const handleSaveBasic = async () => {
    setSaving(true);
    await updateProject(projectId, { name: projectName, description: projectDescription });
    setSaving(false);
  };

  const handleSaveHierarchy = async () => {
    setSaving(true);
    await updateProject(projectId, { hierarchyLabels: [level1, level2, level3] });
    setSaving(false);
  };

  const handleSaveAI = async () => {
    setSaving(true);
    const result = await updateProjectAIConfig(projectId, aiProvider, aiApiKey || null);
    if (!result.success) {
      alert(`保存失败: ${result.error}`);
    } else {
      if (aiApiKey) setAiKeyConfigured(true);
      setAiApiKey("");
    }
    setSaving(false);
  };

  const handleInvite = async () => {
    if (!inviteEmail.trim()) return;
    setSaving(true);
    const result = await addProjectMember(projectId, inviteEmail, inviteRole);
    if (result.success) {
      setInviteEmail("");
      await loadMembers();
    }
    setSaving(false);
  };

  const handleRemoveMember = async (userId: string) => {
    if (!confirm("确认移除该成员？")) return;
    await removeProjectMember(projectId, userId);
    await loadMembers();
  };

  const handleLogout = async () => {
    await logout();
  };

  // F19: Export project as ZIP
  const handleExportProject = async () => {
    setExporting(true);
    try {
      const result = await exportProject(projectId);
      if (result.success) {
        const binary = atob(result.data.content);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: "application/zip" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = result.data.filename;
        a.click();
        URL.revokeObjectURL(url);
      }
    } finally {
      setExporting(false);
    }
  };

  // F20: Migrate project to team
  const handleMigrateToTeam = async () => {
    setMigrating(true);
    const result = await moveProjectTeam(projectId, selectedTeamId || null);
    if (result.success) {
      setMigrateConfirmDialog(false);
      setSelectedTeamId("");
    }
    setMigrating(false);
  };

  const enabledDims = dimensionConfigs.filter((c) => c.enabled);
  const disabledDims = dimensionConfigs.filter((c) => !c.enabled);

  return (
    <div className="bg-background min-h-screen">
      <header className="border-border bg-card flex h-14 items-center justify-between border-b px-6">
        <Link
          href="/projects"
          className="text-foreground hover:text-primary font-semibold transition-colors"
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

      <div className="border-border bg-card border-b px-6 py-3">
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink href="/projects">我的项目</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>
              <ChevronRight className="h-4 w-4" />
            </BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbLink href={`/projects/${projectId}`}>
                {project?.name || "项目"}
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>
              <ChevronRight className="h-4 w-4" />
            </BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbPage>设置</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      <div className="flex">
        <div className="border-border w-[200px] space-y-1 border-r p-4">
          {(
            [
              "basic",
              "dimensions",
              "hierarchy",
              "members",
              "ai",
              "competitors",
              "feed-sources",
              "export",
              "team",
            ] as TabType[]
          ).map((tab) => {
            const labels: Record<TabType, string> = {
              basic: "基本信息",
              dimensions: "维度管理",
              hierarchy: "层级配置",
              members: "成员管理",
              ai: "AI配置",
              competitors: "竞品管理",
              "feed-sources": "订阅源",
              export: "导出项目",
              team: "迁移到团队",
            };
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={cn(
                  "w-full rounded-md px-3 py-2 text-left text-sm transition-colors",
                  activeTab === tab
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground hover:bg-muted",
                )}
              >
                {labels[tab]}
              </button>
            );
          })}
        </div>

        <div className="flex-1 p-6">
          {/* Basic Info Tab */}
          {activeTab === "basic" && (
            <div>
              <h2 className="mb-6 text-lg font-semibold">基本信息</h2>
              <div className="max-w-md space-y-4">
                <div className="space-y-2">
                  <Label>项目名称</Label>
                  <Input value={projectName} onChange={(e) => setProjectName(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>项目描述</Label>
                  <Input
                    value={projectDescription}
                    onChange={(e) => setProjectDescription(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>项目类型</Label>
                  <div className="flex items-center gap-2 py-2">
                    <Badge variant="outline" className="border-blue-200 bg-blue-50 text-blue-700">
                      {project?.templateType || "custom"}
                    </Badge>
                    <span className="text-muted-foreground text-xs">（创建后不可更改）</span>
                  </div>
                </div>
                <Button
                  variant="default"
                  onClick={handleSaveBasic}
                  disabled={saving || !canAdmin}
                  title={!canAdmin ? "查看者无编辑权限" : undefined}
                >
                  {saving ? "保存中..." : "保存"}
                </Button>
              </div>
            </div>
          )}

          {/* Dimensions Management Tab — reads from DB */}
          {activeTab === "dimensions" && (
            <div>
              <h2 className="mb-2 text-lg font-semibold">维度管理</h2>
              <p className="text-muted-foreground mb-6 text-sm">
                配置本项目启用的知识维度和显示顺序
              </p>

              {dimensionConfigs.length === 0 ? (
                <p className="text-muted-foreground text-sm">暂无维度配置，请先通过模板创建项目</p>
              ) : (
                <>
                  <div className="space-y-2">
                    {enabledDims.map((dim) => (
                      <div
                        key={dim.configId}
                        className="border-border flex items-center gap-4 rounded-md border p-3"
                      >
                        <Switch
                          checked={true}
                          onCheckedChange={(checked) =>
                            handleToggleDimension(dim.configId, checked)
                          }
                          disabled={!canAdmin}
                        />
                        <span className="text-sm font-medium">{dim.name}</span>
                        <span className="text-muted-foreground text-sm">{dim.description}</span>
                        <div className="flex-1" />
                        <GripVertical className="text-muted-foreground h-4 w-4 cursor-grab" />
                      </div>
                    ))}
                  </div>

                  {disabledDims.length > 0 && (
                    <>
                      <Separator className="my-6" />
                      <div className="space-y-2">
                        {disabledDims.map((dim) => (
                          <div
                            key={dim.configId}
                            className="border-border flex items-center gap-4 rounded-md border p-3 opacity-60"
                          >
                            <Switch
                              checked={false}
                              onCheckedChange={(checked) =>
                                handleToggleDimension(dim.configId, checked)
                              }
                              disabled={!canAdmin}
                            />
                            <span className="text-muted-foreground text-sm font-medium">
                              {dim.name}
                            </span>
                            <span className="text-muted-foreground text-sm">{dim.description}</span>
                            <div className="flex-1" />
                            <GripVertical className="text-muted-foreground h-4 w-4 cursor-grab" />
                          </div>
                        ))}
                      </div>
                    </>
                  )}

                  <div className="mt-6">
                    <Button
                      variant="default"
                      onClick={handleSaveDimensions}
                      disabled={saving || !canAdmin}
                      title={!canAdmin ? "查看者无编辑权限" : undefined}
                    >
                      {saving ? "保存中..." : "保存"}
                    </Button>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Hierarchy Config Tab */}
          {activeTab === "hierarchy" && (
            <div>
              <h2 className="mb-2 text-lg font-semibold">层级标签配置</h2>
              <p className="text-muted-foreground mb-6 text-sm">自定义本项目的三层结构名称</p>

              <div className="flex gap-8">
                <div className="max-w-xs flex-1 space-y-4">
                  <div className="space-y-2">
                    <Label>第1层</Label>
                    <Input value={level1} onChange={(e) => setLevel1(e.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label>第2层</Label>
                    <Input value={level2} onChange={(e) => setLevel2(e.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label>第3层</Label>
                    <Input value={level3} onChange={(e) => setLevel3(e.target.value)} />
                  </div>
                  <Button
                    variant="default"
                    onClick={handleSaveHierarchy}
                    disabled={saving || !canAdmin}
                    title={!canAdmin ? "查看者无编辑权限" : undefined}
                  >
                    {saving ? "保存中..." : "保存"}
                  </Button>
                </div>

                <Card className="w-[200px] p-4">
                  <h4 className="mb-3 text-sm font-medium">预览</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <Folder className="text-muted-foreground h-4 w-4" />
                      <span>{level1 || "产品线"}</span>
                    </div>
                    <div className="flex items-center gap-2 pl-4">
                      <Folder className="text-muted-foreground h-4 w-4" />
                      <span>{level2 || "模块"}</span>
                    </div>
                    <div className="flex items-center gap-2 pl-8">
                      <File className="text-muted-foreground h-4 w-4" />
                      <span>{level3 || "功能项"}</span>
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          )}

          {/* Members Tab */}
          {activeTab === "members" && (
            <div>
              <div className="mb-6 flex items-center justify-between">
                <h2 className="text-lg font-semibold">成员管理</h2>
                <div className="flex items-center gap-2">
                  <Input
                    placeholder="输入邮箱"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="w-48"
                  />
                  <Select value={inviteRole} onValueChange={(v) => v && setInviteRole(v)}>
                    <SelectTrigger className="w-24">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="admin">管理员</SelectItem>
                      <SelectItem value="editor">编辑者</SelectItem>
                      <SelectItem value="viewer">查看者</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    variant="default"
                    onClick={handleInvite}
                    disabled={saving || !canAdmin}
                    title={!canAdmin ? "查看者无编辑权限" : undefined}
                  >
                    <UserPlus className="mr-2 h-4 w-4" />
                    邀请成员
                  </Button>
                </div>
              </div>

              <div className="border-border overflow-hidden rounded-md border">
                <Table>
                  <TableHeader className="bg-muted/50">
                    <TableRow>
                      <TableHead className="w-12">头像</TableHead>
                      <TableHead>用户名</TableHead>
                      <TableHead>邮箱</TableHead>
                      <TableHead>角色</TableHead>
                      <TableHead className="w-32">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {members.map((member) => {
                      const roleInfo = ROLE_BADGE[member.role] || {
                        label: member.role,
                        variant: "secondary",
                      };
                      return (
                        <TableRow key={member.id}>
                          <TableCell>
                            <Avatar className="h-8 w-8">
                              <AvatarFallback className="bg-muted text-sm">
                                {member.userName?.charAt(0) || "?"}
                              </AvatarFallback>
                            </Avatar>
                          </TableCell>
                          <TableCell className="font-medium">{member.userName}</TableCell>
                          <TableCell className="text-muted-foreground">
                            {member.userEmail}
                          </TableCell>
                          <TableCell>
                            {roleInfo.variant === "green" ? (
                              <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                                {roleInfo.label}
                              </Badge>
                            ) : (
                              <Badge variant={roleInfo.variant as "default" | "secondary"}>
                                {roleInfo.label}
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <button
                              className="text-destructive text-sm hover:underline disabled:cursor-not-allowed disabled:opacity-50"
                              onClick={() => canAdmin && handleRemoveMember(member.userId)}
                              disabled={!canAdmin}
                              title={!canAdmin ? "查看者无编辑权限" : undefined}
                            >
                              移除
                            </button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                    {members.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="text-muted-foreground py-4 text-center">
                          暂无成员
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}

          {/* AI Config Tab */}
          {activeTab === "ai" && (
            <div>
              <h2 className="mb-6 text-lg font-semibold">AI配置</h2>
              <div className="max-w-md space-y-4">
                <div className="space-y-2">
                  <Label>AI Provider</Label>
                  <Select value={aiProvider} onValueChange={(v) => v && setAiProvider(v)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="local">本地模式</SelectItem>
                      <SelectItem value="deepseek">DeepSeek API</SelectItem>
                      <SelectItem value="claude">Claude API</SelectItem>
                      <SelectItem value="codex">Codex API</SelectItem>
                      <SelectItem value="kimi">Kimi API</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>API Key</Label>
                  {aiKeyConfigured && !aiApiKey && (
                    <p className="text-xs text-green-600">已配置（重新输入可更换密钥）</p>
                  )}
                  <Input
                    type="password"
                    placeholder={aiKeyConfigured ? "已配置，留空保持不变" : "sk-..."}
                    value={aiApiKey}
                    onChange={(e) => setAiApiKey(e.target.value)}
                  />
                  <p className="text-muted-foreground text-xs">
                    密钥将加密存储，保存后不可查看原文
                  </p>
                </div>
                <Button
                  variant="default"
                  onClick={handleSaveAI}
                  disabled={saving || !canAdmin}
                  title={!canAdmin ? "查看者无编辑权限" : undefined}
                >
                  {saving ? "保存中..." : "保存配置"}
                </Button>
              </div>
            </div>
          )}

          {/* Competitors Management Tab */}
          {activeTab === "competitors" && (
            <CompetitorManagement
              competitors={competitorsList}
              onCreateCompetitor={handleCreateCompetitor}
              onUpdateCompetitor={handleUpdateCompetitor}
              onDeleteCompetitor={handleDeleteCompetitor}
              canAdmin={canAdmin}
            />
          )}

          {/* Feed Sources Management Tab */}
          {activeTab === "feed-sources" && (
            <div>
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold">订阅源管理</h2>
                  <p className="text-muted-foreground mt-1 text-sm">
                    管理行业动态的 RSS 和搜索订阅源
                  </p>
                </div>
              </div>

              {/* Add new source form */}
              <Card className="mb-6 p-4">
                <h3 className="mb-3 text-sm font-medium">添加新订阅源</h3>
                <div className="flex items-center gap-2">
                  <Input
                    placeholder="名称"
                    value={newFeedName}
                    onChange={(e) => setNewFeedName(e.target.value)}
                    className="w-40"
                  />
                  <Input
                    placeholder="URL"
                    value={newFeedUrl}
                    onChange={(e) => setNewFeedUrl(e.target.value)}
                    className="flex-1"
                  />
                  <Select value={newFeedType} onValueChange={(v) => v && setNewFeedType(v)}>
                    <SelectTrigger className="w-24">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="rss">RSS</SelectItem>
                      <SelectItem value="search">搜索</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    variant="default"
                    size="sm"
                    className="gap-1.5"
                    onClick={handleCreateFeedSource}
                    disabled={!canAdmin || !newFeedName.trim() || !newFeedUrl.trim()}
                  >
                    <Plus className="h-3.5 w-3.5" />
                    添加
                  </Button>
                </div>
              </Card>

              {/* Source list */}
              <div className="space-y-2">
                {feedSourcesList.map((source) => (
                  <div
                    key={source.id}
                    className={cn(
                      "border-border flex items-center justify-between rounded-md border px-4 py-3",
                      !source.isActive && "opacity-60",
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <Rss className="text-muted-foreground h-4 w-4" />
                      <div
                        className={`h-2 w-2 rounded-full ${source.isActive ? "bg-green-500" : "bg-gray-300"}`}
                      />
                      <div>
                        <span className="text-sm font-medium">{source.name}</span>
                        <span className="text-muted-foreground ml-2 text-xs">{source.url}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant="outline" className="text-xs">
                        {source.sourceType}
                      </Badge>
                      <Badge
                        variant={source.isActive ? "default" : "secondary"}
                        className="text-xs"
                      >
                        {source.isActive ? "启用" : "停用"}
                      </Badge>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => handleToggleFeedSource(source.id, !source.isActive)}
                        disabled={!canAdmin}
                      >
                        {source.isActive ? (
                          <Eye className="h-3.5 w-3.5" />
                        ) : (
                          <EyeOff className="text-muted-foreground h-3.5 w-3.5" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-muted-foreground hover:text-destructive h-7 w-7"
                        onClick={() => handleDeleteFeedSource(source.id)}
                        disabled={!canAdmin}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                ))}
                {feedSourcesList.length === 0 && (
                  <div className="text-muted-foreground py-8 text-center text-sm">
                    暂无订阅源，请添加新的订阅源
                  </div>
                )}
              </div>
            </div>
          )}

          {/* F19: Export Project Tab */}
          {activeTab === "export" && (
            <div>
              <h2 className="mb-2 text-lg font-semibold">导出项目</h2>
              <p className="text-muted-foreground mb-6 text-sm">
                将整个项目导出为 ZIP 文件，包含所有模块和功能项的 Markdown 文件
              </p>
              <Card className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Download className="text-muted-foreground h-5 w-5" />
                    <div>
                      <p className="text-sm font-medium">导出完整项目</p>
                      <p className="text-muted-foreground text-xs">包含所有产品线、模块和功能项</p>
                    </div>
                  </div>
                  <Button variant="default" onClick={handleExportProject} disabled={exporting}>
                    <Download className="mr-2 h-4 w-4" />
                    {exporting ? "导出中..." : "导出 ZIP"}
                  </Button>
                </div>
              </Card>
            </div>
          )}

          {/* F20: Migrate to Team Tab */}
          {activeTab === "team" && (
            <div>
              <h2 className="mb-2 text-lg font-semibold">迁移到团队</h2>
              <p className="text-muted-foreground mb-6 text-sm">
                将项目迁移到团队空间，团队成员将可以访问该项目
              </p>
              <div className="max-w-md space-y-4">
                <div className="space-y-2">
                  <Label>选择目标团队</Label>
                  {teamsList.length === 0 ? (
                    <p className="text-muted-foreground py-2 text-sm">
                      你还没有团队，请先
                      <a href="/teams" className="text-primary hover:underline">
                        创建团队
                      </a>
                    </p>
                  ) : (
                    <Select value={selectedTeamId} onValueChange={(v) => v && setSelectedTeamId(v)}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择团队..." />
                      </SelectTrigger>
                      <SelectContent>
                        {teamsList.map((t) => (
                          <SelectItem key={t.id} value={t.id}>
                            {t.name}
                            {t.description ? ` - ${t.description}` : ""}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
                <Button
                  variant="default"
                  onClick={() => setMigrateConfirmDialog(true)}
                  disabled={!selectedTeamId || !canAdmin}
                  title={!canAdmin ? "需要管理员权限" : undefined}
                >
                  <ArrowRightLeft className="mr-2 h-4 w-4" />
                  迁移项目
                </Button>
              </div>

              {/* Migrate Confirm Dialog */}
              {migrateConfirmDialog && (
                <Dialog open={migrateConfirmDialog} onOpenChange={setMigrateConfirmDialog}>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>确认迁移项目</DialogTitle>
                    </DialogHeader>
                    <p className="text-muted-foreground py-4 text-sm">
                      迁移后，项目将归属于所选团队。团队内所有成员将可以访问该项目。
                      你仍然可以在项目设置中将项目迁回个人空间。
                    </p>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setMigrateConfirmDialog(false)}>
                        取消
                      </Button>
                      <Button onClick={handleMigrateToTeam} disabled={migrating}>
                        {migrating ? "迁移中..." : "确认迁移"}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
