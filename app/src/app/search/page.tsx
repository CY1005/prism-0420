"use client";

import Link from "next/link";
import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Search, Bell, LogOut, Bug, Loader2, AlertTriangle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { globalSearch } from "@/actions/search";
import { type SearchResultItem } from "@/services/search";
import { GlobalSearchBar } from "@/components/global-search-bar";

/* ---------- constants ---------- */

type ResultType = "all" | "node" | "dimension" | "issue";
type IssueKind = "bug" | "tech_debt" | "design_flaw" | "performance";

const filterTabs: { key: ResultType; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "node", label: "功能项" },
  { key: "dimension", label: "维度记录" },
  { key: "issue", label: "问题" },
];

const issueKindColor: Record<string, string> = {
  bug: "border-red-200 text-red-700 bg-red-50",
  tech_debt: "border-orange-200 text-orange-700 bg-orange-50",
  design_flaw: "border-purple-200 text-purple-700 bg-purple-50",
  performance: "border-yellow-200 text-yellow-700 bg-yellow-50",
};

const issueKindLabel: Record<string, string> = {
  bug: "Bug",
  tech_debt: "技术债",
  design_flaw: "设计缺陷",
  performance: "性能",
};

const projectColorMap: Record<string, string> = {
  AI云平台: "border-blue-200 text-blue-700 bg-blue-50",
  AI云平台竞品分析: "border-blue-200 text-blue-700 bg-blue-50",
  OpenClaw: "border-green-200 text-green-700 bg-green-50",
  MappingStudio: "border-purple-200 text-purple-700 bg-purple-50",
  Prism: "border-orange-200 text-orange-700 bg-orange-50",
};

function getProjectBadgeClass(name: string | null): string {
  if (!name) return "";
  return projectColorMap[name] || "border-gray-200 text-gray-700 bg-gray-50";
}

const dimensionTypes = ["功能描述", "技术实现", "工程经验", "设计决策", "接口规范"];
const issueCategories: { value: string; label: string }[] = [
  { value: "bug", label: "Bug" },
  { value: "tech_debt", label: "技术债" },
  { value: "design_flaw", label: "设计缺陷" },
  { value: "performance", label: "性能" },
];

/* projects extracted dynamically from search results */

/* ---------- keyword highlight ---------- */

function highlightKeyword(text: string, keyword: string): React.ReactNode {
  if (!keyword.trim()) return text;
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, "gi"));
  return (
    <>
      {parts.map((part, i) =>
        part.toLowerCase() === keyword.toLowerCase() ? (
          <mark key={i} className="rounded bg-yellow-100 px-0.5">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}

/* ---------- inner component (uses useSearchParams) ---------- */

function SearchPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const initialQuery = searchParams.get("q") || "";
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [semanticLoading, setSemanticLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [activeFilter, setActiveFilter] = useState<ResultType>("all");
  const [selectedProjects, setSelectedProjects] = useState<Set<string>>(new Set());
  const [selectedDimensions, setSelectedDimensions] = useState<Set<string>>(
    new Set(dimensionTypes),
  );
  const [selectedIssueCategories, setSelectedIssueCategories] = useState<Set<string>>(
    new Set(issueCategories.map((c) => c.value)),
  );

  // Extract unique projects from results
  const availableProjects = Array.from(
    new Map(
      results
        .filter((r) => r.project_id && r.project_name)
        .map((r) => [r.project_id!, { id: r.project_id!, name: r.project_name! }]),
    ).values(),
  );

  const doSearch = useCallback(
    async (q: string, opts?: { dimensionType?: string; issueCategory?: string }) => {
      if (!q.trim()) return;
      setLoading(true);
      setSemanticLoading(true);
      setError(null);

      const result = await globalSearch(q.trim(), {
        dimensionType: opts?.dimensionType,
        issueCategory: opts?.issueCategory,
        limit: 100,
      });

      setLoading(false);
      if (result.success) {
        setResults(result.data.results);
        setTotal(result.data.total);
        setSearched(true);
        // Initialize project filter with all found projects
        const projectIds = new Set<string>(
          result.data.results
            .filter((r: SearchResultItem) => r.project_id)
            .map((r: SearchResultItem) => r.project_id!),
        );
        setSelectedProjects(projectIds);
        // If any result has semantic match_type, semantic search completed;
        // also stop if search_mode is "keyword" (pgvector unavailable/degraded)
        const hasSemanticInResults = result.data.results.some(
          (r: SearchResultItem) => r.match_type === "semantic" || r.match_type === "both",
        );
        const isKeywordOnly = result.data.search_mode === "keyword";
        setSemanticLoading(!hasSemanticInResults && !isKeywordOnly);
      } else {
        setError(result.error);
        setSearched(true);
        setSemanticLoading(false);
      }
    },
    [],
  );

  // Search on mount if q param exists
  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery);
      doSearch(initialQuery);
    }
  }, [initialQuery, doSearch]);

  const handleSearch = () => {
    if (!query.trim()) return;
    router.push(`/search?q=${encodeURIComponent(query.trim())}`, { scroll: false });
    doSearch(query.trim());
  };

  const toggleProject = (id: string) => {
    setSelectedProjects((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleDimension = (dim: string) => {
    setSelectedDimensions((prev) => {
      const next = new Set(prev);
      if (next.has(dim)) next.delete(dim);
      else next.add(dim);
      return next;
    });
  };

  const toggleIssueCategory = (cat: string) => {
    setSelectedIssueCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  // Client-side filtering of results
  const filteredResults = results.filter((r) => {
    // Type filter
    if (activeFilter !== "all" && r.type !== activeFilter) return false;

    // Project filter (skip if no projects selected yet — means initial state)
    if (selectedProjects.size > 0 && r.project_id && !selectedProjects.has(r.project_id))
      return false;

    // Dimension type filter
    if (r.type === "dimension" && r.dimension_type && !selectedDimensions.has(r.dimension_type))
      return false;

    // Issue category filter
    if (r.type === "issue" && r.issue_category && !selectedIssueCategories.has(r.issue_category))
      return false;

    return true;
  });

  const resultCounts = {
    all: results.length,
    node: results.filter((r) => r.type === "node").length,
    dimension: results.filter((r) => r.type === "dimension").length,
    issue: results.filter((r) => r.type === "issue").length,
  };

  return (
    <div className="bg-background min-h-screen">
      {/* Header */}
      <header className="border-border bg-card flex h-14 items-center justify-between border-b px-6">
        <Link
          href="/projects"
          className="text-foreground hover:text-primary font-semibold transition-colors"
        >
          Prism
        </Link>
        <div className="relative w-96">
          <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <Input
            className="pl-9"
            placeholder="搜索功能、模块、问题..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
        </div>
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <Bell className="text-muted-foreground h-4 w-4" />
          </Button>
          <div className="flex items-center gap-2">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-muted text-sm">陈</AvatarFallback>
            </Avatar>
            <span className="text-foreground text-sm">陈琦</span>
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
            <Link href="/login">
              <LogOut className="text-muted-foreground h-4 w-4" />
            </Link>
          </Button>
        </div>
      </header>

      <div className="flex gap-6 p-6">
        {/* Left Sidebar - Filters */}
        <div className="w-[220px] shrink-0 space-y-6">
          {/* Project Scope */}
          <div>
            <h4 className="mb-2 text-sm font-medium">项目范围</h4>
            <div className="space-y-2">
              {availableProjects.map((project) => (
                <div key={project.id} className="flex items-center gap-2">
                  <Checkbox
                    id={`project-${project.id}`}
                    checked={selectedProjects.has(project.id)}
                    onCheckedChange={() => toggleProject(project.id)}
                  />
                  <label htmlFor={`project-${project.id}`} className="cursor-pointer text-sm">
                    {project.name}
                  </label>
                </div>
              ))}
            </div>
          </div>

          {/* Dimension Type */}
          <div>
            <h4 className="mb-2 text-sm font-medium">维度类型</h4>
            <div className="space-y-2">
              {dimensionTypes.map((dim) => (
                <div key={dim} className="flex items-center gap-2">
                  <Checkbox
                    id={`dim-${dim}`}
                    checked={selectedDimensions.has(dim)}
                    onCheckedChange={() => toggleDimension(dim)}
                  />
                  <label htmlFor={`dim-${dim}`} className="cursor-pointer text-sm">
                    {dim}
                  </label>
                </div>
              ))}
            </div>
          </div>

          {/* Issue Categories */}
          <div>
            <h4 className="mb-2 text-sm font-medium">问题分类</h4>
            <div className="space-y-2">
              {issueCategories.map((cat) => (
                <div key={cat.value} className="flex items-center gap-2">
                  <Checkbox
                    id={`issue-${cat.value}`}
                    checked={selectedIssueCategories.has(cat.value)}
                    onCheckedChange={() => toggleIssueCategory(cat.value)}
                  />
                  <label htmlFor={`issue-${cat.value}`} className="cursor-pointer text-sm">
                    {cat.label}
                  </label>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 space-y-3">
          {/* Filter Tabs */}
          <div className="mb-4 flex items-center gap-2">
            {filterTabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveFilter(tab.key)}
                className={cn(
                  "rounded-full border px-3 py-1.5 text-sm transition-colors",
                  activeFilter === tab.key
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-card text-muted-foreground border-border hover:border-foreground/30",
                )}
              >
                {tab.label}
                {searched && ` (${resultCounts[tab.key]})`}
              </button>
            ))}
          </div>

          {/* Error */}
          {error && (
            <Card className="border-destructive/60 p-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="text-destructive h-4 w-4" />
                <span className="text-destructive text-sm">{error}</span>
              </div>
            </Card>
          )}

          {/* Loading */}
          {loading && (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
              <span className="text-muted-foreground ml-2 text-sm">搜索中...</span>
            </div>
          )}

          {/* Results Summary */}
          {searched && !loading && !error && (
            <>
              <div className="mb-4 flex items-center gap-3">
                <p className="text-muted-foreground text-sm">
                  {filteredResults.length === total
                    ? `找到 ${total} 条结果`
                    : `筛选到 ${filteredResults.length} 条结果（共 ${total} 条）`}
                </p>
                {semanticLoading && (
                  <div className="text-muted-foreground flex items-center gap-1.5 text-xs">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    <span>正在加载语义匹配结果...</span>
                  </div>
                )}
              </div>

              {filteredResults.length === 0 ? (
                <div className="text-muted-foreground py-16 text-center">
                  <Search className="mx-auto mb-2 h-10 w-10 opacity-40" />
                  <p>未找到相关内容，试试其他关键词或调整筛选条件</p>
                </div>
              ) : (
                filteredResults.map((result) => (
                  <Card
                    key={result.id}
                    className="border-border/60 hover:border-primary/30 p-4 shadow-sm transition-colors"
                  >
                    <div className="mb-1 flex items-center gap-2">
                      {result.project_name && (
                        <Badge
                          variant="outline"
                          className={cn("text-xs", getProjectBadgeClass(result.project_name))}
                        >
                          {result.project_name}
                        </Badge>
                      )}
                      {result.type === "issue" && <Bug className="h-3.5 w-3.5 text-red-500" />}
                      <Link
                        href={
                          result.project_id && result.node_id
                            ? `/projects/${result.project_id}/features/${result.node_id}`
                            : result.project_id
                              ? `/projects/${result.project_id}`
                              : "#"
                        }
                        className="text-primary cursor-pointer text-sm font-medium hover:underline"
                      >
                        {highlightKeyword(result.title, query)}
                      </Link>
                      {result.type === "issue" && result.issue_category && (
                        <Badge
                          variant="outline"
                          className={cn("text-xs", issueKindColor[result.issue_category] || "")}
                        >
                          {issueKindLabel[result.issue_category] || result.issue_category}
                        </Badge>
                      )}
                      {result.match_type === "semantic" && (
                        <Badge
                          variant="outline"
                          className="border-violet-200 bg-violet-50 text-xs text-violet-700"
                        >
                          语义匹配
                        </Badge>
                      )}
                      {result.match_type === "both" && (
                        <Badge
                          variant="outline"
                          className="border-violet-200 bg-violet-50 text-xs text-violet-700"
                        >
                          精确+语义
                        </Badge>
                      )}
                    </div>

                    {/* Breadcrumb */}
                    {result.breadcrumb && result.breadcrumb.length > 0 && (
                      <p className="text-muted-foreground text-xs">
                        {result.breadcrumb.join(" → ")}
                      </p>
                    )}
                    {!result.breadcrumb && result.node_path && (
                      <p className="text-muted-foreground text-xs">{result.node_path}</p>
                    )}

                    {/* Content snippet */}
                    <p className="text-foreground/80 mt-2 text-sm">
                      {highlightKeyword(result.content_snippet, query)}
                    </p>

                    {/* Dimension type badge */}
                    {result.type === "dimension" && result.dimension_type && (
                      <Badge variant="secondary" className="mt-2 text-xs">
                        {result.dimension_type}
                      </Badge>
                    )}

                    {/* Node type badge (feature) */}
                    {result.type === "node" && (
                      <Badge variant="secondary" className="mt-2 text-xs">
                        功能描述
                      </Badge>
                    )}
                  </Card>
                ))
              )}
            </>
          )}

          {/* Initial state */}
          {!searched && !loading && (
            <div className="text-muted-foreground py-16 text-center">
              <Search className="mx-auto mb-2 h-10 w-10 opacity-40" />
              <p>输入关键词搜索跨项目的功能模块、维度记录和问题</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ---------- page wrapper with Suspense ---------- */

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="bg-background flex min-h-screen items-center justify-center">
          <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
        </div>
      }
    >
      <SearchPageInner />
    </Suspense>
  );
}
