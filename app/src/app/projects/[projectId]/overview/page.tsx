"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, useEffect } from "react";
import {
  Bell,
  ChevronRight,
  LogOut,
  Settings,
  Shield,
  Upload,
  FolderUp,
  Plus,
  Loader2,
  FileUp,
  LayoutTemplate,
  Clock,
  Bot,
  Rss,
  Eye,
  EyeOff,
  Trash2,
  X,
} from "lucide-react";
import { ImportCSVModal } from "@/components/import-csv-modal";
import { GlobalSearchBar } from "@/components/global-search-bar";
import { TreemapView } from "@/components/treemap-view";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  type ProjectStats,
  type TreeNodeOverview,
  getProjectStatsAction,
  getProjectTreeOverviewAction,
} from "@/actions/project-stats-proxy";
import { getPanoramaData, getProjectStats as getPanoramaStats } from "@/actions/panorama";
import { getActivityLogs } from "@/actions/activity-log";
import { getProject } from "@/actions/projects";
import { getSessionUser } from "@/actions/auth";
import {
  getFeedItems,
  getFeedSources,
  confirmFeedItem,
  ignoreFeedItem,
  createFeedSource,
  updateFeedSource,
  deleteFeedSource,
} from "@/actions/feed";
import { FeedList, type FeedItemData } from "@/components/feed-card";
import { useProjectRole } from "@/contexts/project-role-context";
import { Input as FormInput } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function getStatusColor(percent: number) {
  if (percent >= 80) return "bg-green-500";
  if (percent >= 40) return "bg-yellow-500";
  return "bg-red-500";
}

/** Transform top-level tree nodes into the layers visualization format */
function treeToLayers(tree: TreeNodeOverview[]) {
  return tree.map((node) => ({
    name: node.name,
    completion: Math.round(node.completion_percent),
    modules: node.children.map((child) => ({
      name: child.name,
      completion: Math.round(child.completion_percent),
    })),
  }));
}

function RecentUpdatesSidebar({ projectId }: { projectId: string }) {
  const [logs, setLogs] = useState<{ id: string; summary: string; createdAt: string | Date }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getActivityLogs(projectId, 1, 5).then((r) => {
      setLogs(r.logs as typeof logs);
      setLoading(false);
    });
  }, [projectId]);

  return (
    <Card className="border-border/60 w-[280px] p-4 shadow-sm">
      <h3 className="text-foreground mb-4 font-medium">最近更新</h3>
      {loading ? (
        <div className="text-muted-foreground flex items-center gap-2 py-4 text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          加载中...
        </div>
      ) : logs.length === 0 ? (
        <p className="text-muted-foreground py-4 text-sm">暂无更新记录</p>
      ) : (
        <div className="space-y-0">
          {logs.map((log, index) => {
            const time =
              typeof log.createdAt === "string" ? new Date(log.createdAt) : log.createdAt;
            const timeStr =
              time instanceof Date && !isNaN(time.getTime())
                ? time.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" })
                : "";
            return (
              <div key={log.id}>
                <div className="py-3">
                  <p className="text-foreground text-sm">{log.summary}</p>
                  <p className="text-muted-foreground mt-1 text-xs">{timeStr}</p>
                </div>
                {index < logs.length - 1 && <Separator />}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

export default function ProjectOverviewPage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const { isViewer } = useProjectRole();
  const [isEmptyProject, setIsEmptyProject] = useState(projectId === "3");
  const [csvModalOpen, setCsvModalOpen] = useState(false);
  const [realStats, setRealStats] = useState<ProjectStats | null>(null);
  const [realTree, setRealTree] = useState<TreeNodeOverview[] | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [treeLoading, setTreeLoading] = useState(true);
  const [apiError, setApiError] = useState<string | null>(null);
  const [activeSubTab, setActiveSubTab] = useState<"treemap" | "tree">("treemap");
  const [panoramaData, setPanoramaData] = useState<Awaited<
    ReturnType<typeof getPanoramaData>
  > | null>(null);
  const [panoramaLoading, setPanoramaLoading] = useState(true);
  const [projectName, setProjectName] = useState("");
  const [userName, setUserName] = useState("");
  const [userInitials, setUserInitials] = useState("");
  const [panoramaStats, setPanoramaStatsData] = useState<{
    totalModules: number;
    totalFeatures: number;
    avgCompletion: number;
    lastUpdatedAt: Date | null;
  } | null>(null);

  // F15: Activity log state
  const [showActivityLog, setShowActivityLog] = useState(false);
  const [activityLogs, setActivityLogs] = useState<
    {
      id: string;
      actionType: string;
      targetType: string;
      summary: string;
      createdAt: string | Date;
      metadata: Record<string, unknown> | null;
    }[]
  >([]);
  const [activityPage, setActivityPage] = useState(1);
  const [activityLoading, setActivityLoading] = useState(false);

  // F14: Feed state
  const [showFeed, setShowFeed] = useState(false);
  const [feedItemsList, setFeedItemsList] = useState<FeedItemData[]>([]);
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
  const [feedLoading, setFeedLoading] = useState(false);
  const [feedStatusFilter, setFeedStatusFilter] = useState<string>("all");
  const [showFeedSources, setShowFeedSources] = useState(false);
  const [newSourceName, setNewSourceName] = useState("");
  const [newSourceUrl, setNewSourceUrl] = useState("");
  const [newSourceType, setNewSourceType] = useState("rss");

  const loadFeedData = async (statusFilter: string) => {
    setFeedLoading(true);
    try {
      const statuses =
        statusFilter === "all" ? ["pending", "confirmed", "ignored"] : [statusFilter];
      const allItems: FeedItemData[] = [];
      for (const s of statuses) {
        const items = await getFeedItems(projectId, s);
        allItems.push(...(items as FeedItemData[]));
      }
      setFeedItemsList(allItems);
      const sources = await getFeedSources(projectId);
      setFeedSourcesList(sources as typeof feedSourcesList);
    } catch {
      // ignore
    } finally {
      setFeedLoading(false);
    }
  };

  useEffect(() => {
    if (showFeed) {
      loadFeedData(feedStatusFilter);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showFeed, feedStatusFilter]);

  const handleConfirmFeed = async (itemId: string, nodeId: string) => {
    await confirmFeedItem(itemId, nodeId);
    loadFeedData(feedStatusFilter);
  };

  const handleIgnoreFeed = async (itemId: string) => {
    await ignoreFeedItem(itemId);
    loadFeedData(feedStatusFilter);
  };

  const handleAddSource = async () => {
    if (!newSourceName.trim() || !newSourceUrl.trim()) return;
    await createFeedSource(projectId, {
      name: newSourceName.trim(),
      url: newSourceUrl.trim(),
      sourceType: newSourceType,
    });
    setNewSourceName("");
    setNewSourceUrl("");
    loadFeedData(feedStatusFilter);
  };

  const handleToggleSource = async (sourceId: string, isActive: boolean) => {
    await updateFeedSource(sourceId, { isActive });
    loadFeedData(feedStatusFilter);
  };

  const handleDeleteSource = async (sourceId: string) => {
    await deleteFeedSource(sourceId);
    loadFeedData(feedStatusFilter);
  };

  const feedPendingCount = feedItemsList.filter((i) => i.status === "pending").length;

  useEffect(() => {
    // Load project name and user info
    getProject(projectId).then((p) => {
      if (p) setProjectName(p.name);
    });
    getSessionUser().then((u) => {
      if (u) {
        setUserName(u.name);
        setUserInitials(u.name.charAt(0));
      }
    });

    setStatsLoading(true);
    getProjectStatsAction(projectId).then((r) => {
      setStatsLoading(false);
      if (r.success) setRealStats(r.data);
      else setApiError(r.error);
    });

    setTreeLoading(true);
    getProjectTreeOverviewAction(projectId).then((r) => {
      setTreeLoading(false);
      if (r.success) setRealTree(r.data.tree);
      else setApiError((prev) => prev ?? r.error);
    });

    // Load panorama data
    setPanoramaLoading(true);
    getPanoramaData(projectId).then((r) => {
      setPanoramaLoading(false);
      setPanoramaData(r);
    });

    getPanoramaStats(projectId).then((r) => {
      if (r.success) setPanoramaStatsData(r.data);
    });
  }, [projectId]);

  // F15: Load activity logs
  const loadActivityLogs = async (page: number) => {
    setActivityLoading(true);
    try {
      const result = await getActivityLogs(projectId, page, 20);
      if (page === 1) {
        setActivityLogs(result.logs as typeof activityLogs);
      } else {
        setActivityLogs((prev) => [...prev, ...(result.logs as typeof activityLogs)]);
      }
      setActivityPage(page);
    } finally {
      setActivityLoading(false);
    }
  };

  useEffect(() => {
    if (showActivityLog && activityLogs.length === 0) {
      loadActivityLogs(1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showActivityLog]);

  // Stats: real data only; show loading/error states in render
  const statsData = realStats
    ? {
        line1: `${realStats.total_folders} 个`,
        line2: `${realStats.total_folders + realStats.total_files} 个`,
        line3: `${realStats.total_files} 个`,
        line4: `${Math.round(realStats.avg_completion_percent)}%`,
        avgPercent: Math.round(realStats.avg_completion_percent),
      }
    : null;

  // Layers: use real tree data when available
  const layers = realTree ? treeToLayers(realTree) : null;

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
          <Link
            href="/admin"
            className="hover:bg-accent inline-flex h-8 w-8 items-center justify-center rounded-md"
          >
            <Shield className="text-muted-foreground h-4 w-4" />
          </Link>
          <Link
            href={`/projects/${projectId}/settings`}
            className="hover:bg-accent inline-flex h-8 w-8 items-center justify-center rounded-md"
          >
            <Settings className="text-muted-foreground h-4 w-4" />
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
          <Link
            href="/login"
            className="hover:bg-accent inline-flex h-8 w-8 items-center justify-center rounded-md"
          >
            <LogOut className="text-muted-foreground h-4 w-4" />
          </Link>
        </div>
      </header>

      <div className="px-6 py-4">
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink href="/projects">我的项目</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>
              <ChevronRight className="h-4 w-4" />
            </BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbPage className="flex items-center gap-2">
                {projectName || "加载中..."}
              </BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      <div className="border-border flex items-center gap-6 border-b px-6">
        <Link
          href={`/projects/${projectId}/overview`}
          className="border-primary text-primary border-b-2 pt-2 pb-3 text-sm font-medium"
        >
          全景图
        </Link>
        <Link
          href={`/projects/${projectId}/product-lines/private-cloud`}
          className="text-muted-foreground hover:text-foreground pt-2 pb-3 text-sm"
        >
          产品线
        </Link>
        <Link
          href={`/projects/${projectId}/analysis`}
          className="text-muted-foreground hover:text-foreground pt-2 pb-3 text-sm"
        >
          需求工作台
        </Link>
        <Link
          href={`/projects/${projectId}/comparison`}
          className="text-muted-foreground hover:text-foreground pt-2 pb-3 text-sm"
        >
          竞品对比
        </Link>
        <Link
          href={`/projects/${projectId}/issues`}
          className="text-muted-foreground hover:text-foreground pt-2 pb-3 text-sm"
        >
          问题沉淀
        </Link>
        <Link
          href={`/projects/${projectId}/relation-graph`}
          className="text-muted-foreground hover:text-foreground pt-2 pb-3 text-sm"
        >
          关系图
        </Link>
        <button
          onClick={() => {
            setShowFeed(!showFeed);
            if (showActivityLog) setShowActivityLog(false);
          }}
          className={`pt-2 pb-3 text-sm ${
            showFeed
              ? "border-primary text-primary border-b-2 font-medium"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          行业动态
        </button>
        <button
          onClick={() => {
            setShowActivityLog(!showActivityLog);
            if (showFeed) setShowFeed(false);
          }}
          className={`pt-2 pb-3 text-sm ${
            showActivityLog
              ? "border-primary text-primary border-b-2 font-medium"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          活动日志
        </button>
        <div className="flex-1" />
        <Link
          href={`/projects/${projectId}/settings`}
          className="text-muted-foreground hover:text-foreground flex items-center gap-1 pt-2 pb-3 text-sm"
        >
          <Settings className="h-3.5 w-3.5" />
          设置
        </Link>
      </div>

      {apiError && (
        <div className="mx-6 mt-2 rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
          数据加载失败：{apiError}
        </div>
      )}

      <div className="flex items-center gap-4 px-6 py-4">
        <div className="grid flex-1 grid-cols-4 gap-4">
          {statsLoading && !isEmptyProject ? (
            <div className="text-muted-foreground col-span-4 flex items-center gap-2 py-4 text-sm">
              <Loader2 className="h-4 w-4 animate-spin" />
              加载统计数据中...
            </div>
          ) : (
            <>
              <Card className="border-border/60 p-4 shadow-sm">
                <span className="text-foreground text-2xl font-bold">
                  {isEmptyProject ? "0" : (statsData?.line1 ?? "—")}
                </span>
                <p className="text-muted-foreground text-sm">产品线</p>
              </Card>
              <Card className="border-border/60 p-4 shadow-sm">
                <span className="text-foreground text-2xl font-bold">
                  {isEmptyProject ? "0" : (statsData?.line2 ?? "—")}
                </span>
                <p className="text-muted-foreground text-sm">功能模块</p>
              </Card>
              <Card className="border-border/60 p-4 shadow-sm">
                <span className="text-foreground text-2xl font-bold">
                  {isEmptyProject ? "0" : (statsData?.line3 ?? "—")}
                </span>
                <p className="text-muted-foreground text-sm">功能项</p>
              </Card>
              <Card className="border-border/60 p-4 shadow-sm">
                <span className="text-foreground text-2xl font-bold">
                  {isEmptyProject ? "0%" : (statsData?.line4 ?? "—")}
                </span>
                <p className="text-muted-foreground text-sm">平均完善度</p>
                <Progress
                  value={isEmptyProject ? 0 : (statsData?.avgPercent ?? 0)}
                  className="mt-2 h-2"
                />
              </Card>
            </>
          )}
        </div>
        {isViewer ? (
          <span
            title="查看者无编辑权限"
            className="border-border bg-background inline-flex cursor-not-allowed items-center gap-2 rounded-md border px-4 py-3 text-sm font-medium opacity-50"
          >
            <Upload className="h-4 w-4" />
            <span>导入数据</span>
          </span>
        ) : (
          <Link
            href={`/projects/${projectId}/import`}
            className="border-border bg-background hover:bg-accent inline-flex items-center gap-2 rounded-md border px-4 py-3 text-sm font-medium transition-colors"
          >
            <Upload className="h-4 w-4" />
            <span>导入数据</span>
          </Link>
        )}
      </div>

      {/* Sub-tabs: 全景图 / 关系图 */}
      <div className="flex items-center gap-4 px-6 pb-4">
        <button
          onClick={() => setActiveSubTab("treemap")}
          className={`border-b-2 pb-1 text-sm font-medium transition-colors ${
            activeSubTab === "treemap"
              ? "border-primary text-primary"
              : "text-muted-foreground hover:text-foreground border-transparent"
          }`}
        >
          全景图
        </button>
        <Link
          href={`/projects/${projectId}/relation-graph`}
          className="text-muted-foreground hover:text-foreground border-b-2 border-transparent pb-1 text-sm font-medium transition-colors"
        >
          关系图
        </Link>
        <button
          onClick={() => setActiveSubTab("tree")}
          className={`border-b-2 pb-1 text-sm font-medium transition-colors ${
            activeSubTab === "tree"
              ? "border-primary text-primary"
              : "text-muted-foreground hover:text-foreground border-transparent"
          }`}
        >
          树形视图
        </button>
      </div>

      <div className="flex flex-1 gap-6 px-6 pb-6">
        {isEmptyProject && !treeLoading && (realTree === null || realTree.length === 0) ? (
          <>
            <ImportCSVModal
              projectId={projectId}
              open={csvModalOpen}
              onOpenChange={(open) => {
                setCsvModalOpen(open);
                if (!open) {
                  setTreeLoading(true);
                  getProjectTreeOverviewAction(projectId).then((r) => {
                    setTreeLoading(false);
                    if (r.success) {
                      setRealTree(r.data.tree);
                      if (r.data.tree.length > 0) setIsEmptyProject(false);
                    }
                  });
                }
              }}
            />
            <Card className="border-border/60 flex min-h-[400px] flex-1 flex-col items-center justify-center p-6 shadow-sm">
              <div className="flex max-w-lg flex-col items-center text-center">
                <div className="bg-muted mb-6 flex h-16 w-16 items-center justify-center rounded-full">
                  <FolderUp className="text-muted-foreground h-8 w-8" />
                </div>
                <h2 className="text-foreground mb-2 text-xl font-semibold">开始构建你的知识库</h2>
                <p className="text-muted-foreground mb-8 text-sm">
                  选择一种方式初始化项目结构，快速搭建你的知识体系
                </p>
                <div className="grid w-full grid-cols-3 gap-4">
                  <Link
                    href={`/projects/${projectId}/product-lines/private-cloud`}
                    className="border-border bg-background hover:border-primary/50 hover:bg-primary/5 group flex flex-col items-center gap-3 rounded-xl border p-5 text-center transition-all"
                  >
                    <div className="bg-muted group-hover:bg-primary/10 flex h-10 w-10 items-center justify-center rounded-lg transition-colors">
                      <Plus className="text-muted-foreground group-hover:text-primary h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-foreground text-sm font-medium">手动创建</p>
                      <p className="text-muted-foreground mt-0.5 text-xs">逐步添加节点</p>
                    </div>
                  </Link>
                  <button
                    onClick={() => !isViewer && setCsvModalOpen(true)}
                    disabled={isViewer}
                    title={isViewer ? "查看者无编辑权限" : undefined}
                    className="border-border bg-background hover:border-primary/50 hover:bg-primary/5 group flex flex-col items-center gap-3 rounded-xl border p-5 text-center transition-all disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <div className="bg-muted group-hover:bg-primary/10 flex h-10 w-10 items-center justify-center rounded-lg transition-colors">
                      <FileUp className="text-muted-foreground group-hover:text-primary h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-foreground text-sm font-medium">CSV 导入</p>
                      <p className="text-muted-foreground mt-0.5 text-xs">批量导入结构</p>
                    </div>
                  </button>
                  <button
                    disabled
                    title="即将推出"
                    className="border-border bg-background flex cursor-not-allowed flex-col items-center gap-3 rounded-xl border p-5 text-center opacity-50"
                  >
                    <div className="bg-muted flex h-10 w-10 items-center justify-center rounded-lg">
                      <LayoutTemplate className="text-muted-foreground h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-foreground text-sm font-medium">模板初始化</p>
                      <p className="text-muted-foreground mt-0.5 text-xs">即将推出</p>
                    </div>
                  </button>
                </div>
              </div>
            </Card>
          </>
        ) : activeSubTab === "treemap" ? (
          <Card className="border-border/60 flex-1 p-6 shadow-sm">
            {panoramaLoading ? (
              <div className="text-muted-foreground flex items-center justify-center gap-2 py-8 text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                加载全景图数据中...
              </div>
            ) : panoramaData?.success && panoramaData.data.length > 0 ? (
              <TreemapView projectId={projectId} initialData={panoramaData.data} />
            ) : (
              <div className="text-muted-foreground flex items-center justify-center py-8 text-sm">
                暂无全景图数据
              </div>
            )}
          </Card>
        ) : (
          <Card className="border-border/60 flex-1 p-6 shadow-sm">
            {treeLoading ? (
              <div className="text-muted-foreground flex items-center justify-center gap-2 py-8 text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                加载结构数据中...
              </div>
            ) : layers && layers.length > 0 ? (
              <div className="flex gap-6">
                {layers.map((line) => (
                  <div key={line.name} className="flex flex-col items-center">
                    <div className="border-border bg-card flex items-center gap-2 rounded-lg border p-3">
                      <span className={`h-2 w-2 rounded-full ${getStatusColor(line.completion)}`} />
                      <span className="text-foreground text-sm font-medium">{line.name}</span>
                    </div>
                    <div className="bg-border h-4 w-px" />
                    <div className="flex flex-col gap-2">
                      {line.modules.map((module, index) => (
                        <div key={module.name} className="flex flex-col items-center">
                          {index > 0 && <div className="bg-border h-2 w-px" />}
                          <Link
                            href="/"
                            className="border-border bg-muted/30 hover:border-primary/40 hover:bg-primary/5 flex cursor-pointer items-center gap-2 rounded-md border p-2 transition-all"
                          >
                            <span
                              className={`h-1.5 w-1.5 rounded-full ${getStatusColor(module.completion)}`}
                            />
                            <span className="text-foreground text-xs">{module.name}</span>
                          </Link>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-muted-foreground flex items-center justify-center py-8 text-sm">
                暂无结构数据
              </div>
            )}
          </Card>
        )}

        <RecentUpdatesSidebar projectId={projectId} />
      </div>

      {/* F14: Feed Panel */}
      {showFeed && (
        <div className="px-6 pb-6">
          {/* AI Auto-search Indicator */}
          <div className="bg-muted/30 border-border flex items-center justify-between rounded-t-lg border border-b-0 px-4 py-3">
            <div className="text-muted-foreground flex items-center gap-2 text-sm">
              <Bot className="text-primary h-4 w-4" />
              <span>AI 基于项目知识库自动搜索</span>
              {feedPendingCount > 0 && (
                <Badge variant="secondary" className="ml-2">
                  {feedPendingCount} 条待确认
                </Badge>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => setShowFeedSources(!showFeedSources)}
            >
              <Rss className="h-3.5 w-3.5" />
              {showFeedSources ? "隐藏订阅源" : "管理订阅源"}
            </Button>
          </div>

          {/* RSS Sources Panel */}
          {showFeedSources && (
            <div className="border-border bg-card border border-b-0 px-4 py-4">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-medium">RSS 订阅源</h3>
              </div>
              <div className="mb-4 space-y-2">
                {feedSourcesList.map((source) => (
                  <div
                    key={source.id}
                    className="border-border flex items-center justify-between rounded-md border px-3 py-2"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`h-2 w-2 rounded-full ${source.isActive ? "bg-green-500" : "bg-gray-300"}`}
                      />
                      <span className="text-sm font-medium">{source.name}</span>
                      <span className="text-muted-foreground text-xs">{source.url}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant="outline" className="text-xs">
                        {source.sourceType}
                      </Badge>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => handleToggleSource(source.id, !source.isActive)}
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
                        className="text-muted-foreground hover:text-destructive h-6 w-6"
                        onClick={() => handleDeleteSource(source.id)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                ))}
                {feedSourcesList.length === 0 && (
                  <p className="text-muted-foreground py-2 text-center text-sm">暂无订阅源</p>
                )}
              </div>
              <Separator className="mb-3" />
              <div className="flex items-center gap-2">
                <FormInput
                  placeholder="名称"
                  value={newSourceName}
                  onChange={(e) => setNewSourceName(e.target.value)}
                  className="w-32"
                />
                <FormInput
                  placeholder="URL"
                  value={newSourceUrl}
                  onChange={(e) => setNewSourceUrl(e.target.value)}
                  className="flex-1"
                />
                <Select value={newSourceType} onValueChange={(v) => v && setNewSourceType(v)}>
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
                  onClick={handleAddSource}
                  disabled={!newSourceName.trim() || !newSourceUrl.trim()}
                >
                  添加
                </Button>
              </div>
            </div>
          )}

          {/* Filter + Feed List */}
          <Card className="border-border/60 rounded-t-none border-t-0 p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-semibold">行业动态 Feed</h2>
                <Badge variant="secondary">{feedItemsList.length} 条</Badge>
              </div>
              <Select value={feedStatusFilter} onValueChange={(v) => v && setFeedStatusFilter(v)}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="pending">待确认</SelectItem>
                  <SelectItem value="confirmed">已关联</SelectItem>
                  <SelectItem value="ignored">已忽略</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {feedLoading ? (
              <div className="text-muted-foreground flex items-center justify-center gap-2 py-8 text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                加载动态中...
              </div>
            ) : (
              <FeedList
                items={feedItemsList}
                onConfirm={handleConfirmFeed}
                onIgnore={handleIgnoreFeed}
              />
            )}
          </Card>
        </div>
      )}

      {/* F15: Activity Log Panel */}
      {showActivityLog && (
        <div className="px-6 pb-6">
          <Card className="border-border/60 p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="text-muted-foreground h-5 w-5" />
                <h2 className="text-lg font-semibold">活动日志</h2>
                <Badge variant="secondary" className="text-xs">
                  {activityLogs.length} 条
                </Badge>
              </div>
            </div>

            {activityLoading && activityLogs.length === 0 ? (
              <div className="text-muted-foreground flex items-center justify-center gap-2 py-8 text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                加载活动日志中...
              </div>
            ) : activityLogs.length === 0 ? (
              <div className="text-muted-foreground py-8 text-center text-sm">暂无活动记录</div>
            ) : (
              <div className="space-y-0">
                {activityLogs.map((log) => {
                  const time =
                    typeof log.createdAt === "string" ? new Date(log.createdAt) : log.createdAt;
                  return (
                    <div
                      key={log.id}
                      className="border-border/60 flex items-center gap-3 border-b py-3 last:border-0"
                    >
                      <div className="bg-muted flex h-8 w-8 shrink-0 items-center justify-center rounded-full">
                        <Clock className="text-muted-foreground h-3.5 w-3.5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm">{log.summary}</p>
                        <div className="mt-0.5 flex items-center gap-2">
                          <Badge variant="secondary" className="text-xs">
                            {log.actionType}
                          </Badge>
                          <span className="text-muted-foreground text-xs">{log.targetType}</span>
                        </div>
                      </div>
                      <span className="text-muted-foreground shrink-0 text-xs">
                        {time instanceof Date && !isNaN(time.getTime())
                          ? time.toLocaleString("zh-CN", {
                              month: "2-digit",
                              day: "2-digit",
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : String(log.createdAt)}
                      </span>
                    </div>
                  );
                })}

                {/* Load more */}
                <div className="flex justify-center pt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => loadActivityLogs(activityPage + 1)}
                    disabled={activityLoading}
                  >
                    {activityLoading ? (
                      <>
                        <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                        加载中...
                      </>
                    ) : (
                      "加载更多"
                    )}
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
