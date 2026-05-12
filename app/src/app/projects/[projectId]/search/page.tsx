"use client";

import Link from "next/link";
import { useState, useEffect, useCallback, Suspense, use } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Search, Loader2, AlertTriangle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { globalSearch } from "@/actions/search";
import { GlobalSearchBar } from "@/components/global-search-bar";
import type { components } from "@/types/api";

// Phase 2.3 cleanup C: 项目内全文搜索结果页 / M18 hybrid + RRF（design §7 line 616）
// 路径：/projects/[projectId]/search?q=...
// 已删 prism v1 旧 /search 全局搜索路由 + services/search.ts legacy 栈

type SearchResultItem = components["schemas"]["SearchResultItem"];
type EmbeddingTargetType = components["schemas"]["EmbeddingTargetType"];

const filterTabs: { key: "all" | EmbeddingTargetType; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "node", label: "功能项" },
  { key: "dimension_record", label: "维度记录" },
  { key: "issue", label: "问题" },
  { key: "competitor", label: "竞品" },
];

const targetTypeColor: Record<string, string> = {
  node: "border-blue-200 text-blue-700 bg-blue-50",
  dimension_record: "border-green-200 text-green-700 bg-green-50",
  issue: "border-red-200 text-red-700 bg-red-50",
  competitor: "border-purple-200 text-purple-700 bg-purple-50",
};

const targetTypeLabel: Record<string, string> = {
  node: "功能项",
  dimension_record: "维度记录",
  issue: "问题",
  competitor: "竞品",
};

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

function ProjectSearchPageInner({ projectId }: { projectId: string }) {
  const searchParams = useSearchParams();
  const router = useRouter();

  const initialQuery = searchParams.get("q") || "";
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [total, setTotal] = useState(0);
  const [searchMode, setSearchMode] = useState<"hybrid" | "keyword_only">("hybrid");
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<"all" | EmbeddingTargetType>("all");

  const doSearch = useCallback(
    async (q: string) => {
      if (!q.trim()) return;
      setLoading(true);
      setError(null);

      const result = await globalSearch(q.trim(), { projectId, limit: 100 });

      setLoading(false);
      if (result.success) {
        setResults(result.data.results);
        setTotal(result.data.total);
        setSearchMode(result.data.search_mode);
        setSearched(true);
      } else {
        setError(result.error);
        setSearched(true);
      }
    },
    [projectId],
  );

  useEffect(() => {
    if (!initialQuery) return;
    // 从 URL ?q= 触发初始搜索；doSearch 内部 setState 是必要的副作用
    // （React 19 的 set-state-in-effect 规则推荐 server fetch / SWR，但这里
    // 是 query param driven 的 client search，无法避免）
    // eslint-disable-next-line react-hooks/set-state-in-effect
    doSearch(initialQuery);
  }, [initialQuery, doSearch]);

  const handleSearch = () => {
    if (!query.trim()) return;
    router.push(`/projects/${projectId}/search?q=${encodeURIComponent(query.trim())}`, {
      scroll: false,
    });
    doSearch(query.trim());
  };

  const filteredResults =
    activeFilter === "all" ? results : results.filter((r) => r.target_type === activeFilter);

  const resultCounts: Record<string, number> = {
    all: results.length,
    node: results.filter((r) => r.target_type === "node").length,
    dimension_record: results.filter((r) => r.target_type === "dimension_record").length,
    issue: results.filter((r) => r.target_type === "issue").length,
    competitor: results.filter((r) => r.target_type === "competitor").length,
  };

  const buildResultLink = (item: SearchResultItem): string => {
    if (item.target_type === "node") {
      return `/projects/${projectId}/features/${item.target_id}`;
    }
    if (item.target_type === "issue") {
      return `/projects/${projectId}/issues`;
    }
    return `/projects/${projectId}`;
  };

  return (
    <div className="bg-background min-h-screen">
      <header className="border-border bg-card flex h-14 items-center justify-between border-b px-6">
        <Link
          href={`/projects/${projectId}`}
          className="text-foreground hover:text-primary font-semibold transition-colors"
        >
          Prism
        </Link>
        <div className="relative w-96">
          <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <Input
            className="pl-9"
            placeholder="搜索功能、维度、问题、竞品..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
        </div>
        <GlobalSearchBar />
      </header>

      <div className="mx-auto max-w-5xl space-y-3 p-6">
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

        {error && (
          <Card className="border-destructive/60 p-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="text-destructive h-4 w-4" />
              <span className="text-destructive text-sm">{error}</span>
            </div>
          </Card>
        )}

        {loading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
            <span className="text-muted-foreground ml-2 text-sm">搜索中...</span>
          </div>
        )}

        {searched && !loading && !error && (
          <>
            <div className="mb-4 flex items-center gap-3">
              <p className="text-muted-foreground text-sm">
                {filteredResults.length === total
                  ? `找到 ${total} 条结果`
                  : `筛选到 ${filteredResults.length} 条结果（共 ${total} 条）`}
              </p>
              {searchMode === "keyword_only" && (
                <Badge variant="outline" className="text-xs">
                  仅关键词（pgvector 不可用）
                </Badge>
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
                  key={result.target_id}
                  className="border-border/60 hover:border-primary/30 p-4 shadow-sm transition-colors"
                >
                  <div className="mb-1 flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={cn("text-xs", targetTypeColor[result.target_type])}
                    >
                      {targetTypeLabel[result.target_type] ?? result.target_type}
                    </Badge>
                    <Link
                      href={buildResultLink(result)}
                      className="text-primary cursor-pointer text-sm font-medium hover:underline"
                    >
                      {highlightKeyword(result.title, query)}
                    </Link>
                    {result.matched_by.includes("semantic") && (
                      <Badge
                        variant="outline"
                        className="border-violet-200 bg-violet-50 text-xs text-violet-700"
                      >
                        {result.matched_by.includes("keyword") ? "精确+语义" : "语义匹配"}
                      </Badge>
                    )}
                  </div>
                  {result.breadcrumb && result.breadcrumb.length > 0 && (
                    <p className="text-muted-foreground text-xs">{result.breadcrumb.join(" → ")}</p>
                  )}
                  <p className="text-foreground/80 mt-2 text-sm">
                    {highlightKeyword(result.snippet, query)}
                  </p>
                </Card>
              ))
            )}
          </>
        )}

        {!searched && !loading && (
          <div className="text-muted-foreground py-16 text-center">
            <Search className="mx-auto mb-2 h-10 w-10 opacity-40" />
            <p>输入关键词搜索项目内的功能模块、维度记录和问题</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ProjectSearchPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = use(params);
  return (
    <Suspense
      fallback={
        <div className="bg-background flex min-h-screen items-center justify-center">
          <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
        </div>
      }
    >
      <ProjectSearchPageInner projectId={projectId} />
    </Suspense>
  );
}
