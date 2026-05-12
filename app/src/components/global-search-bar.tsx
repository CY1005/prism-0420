"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { globalSearch } from "@/actions/search";
import type { components } from "@/types/api";
import { cn } from "@/lib/utils";

// Phase 2.3 cleanup C: 直接用 M18 codegen SearchResultItem（snake_case，含 target_type/
// target_id/snippet/matched_by/breadcrumb/score/title）。component 在 projectId 上下文内
// 才渲染（非项目页 useParams 返 undefined → 不渲染）。
type SearchResultItem = components["schemas"]["SearchResultItem"];

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

export function GlobalSearchBar() {
  const router = useRouter();
  const params = useParams();
  const projectId = typeof params?.projectId === "string" ? params.projectId : undefined;

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = useCallback(
    async (q: string) => {
      if (!q.trim() || !projectId) {
        setResults([]);
        setOpen(false);
        return;
      }
      setLoading(true);
      const result = await globalSearch(q.trim(), { projectId, limit: 5 });
      setLoading(false);
      if (result.success) {
        setResults(result.data.results);
        setOpen(result.data.results.length > 0);
      } else {
        setResults([]);
        setOpen(false);
      }
    },
    [projectId],
  );

  const handleChange = (value: string) => {
    setQuery(value);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSearch(value), 300);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && query.trim() && projectId) {
      setOpen(false);
      router.push(`/projects/${projectId}/search?q=${encodeURIComponent(query.trim())}`);
    }
    if (e.key === "Escape") {
      setOpen(false);
    }
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleResultClick = (item: SearchResultItem) => {
    if (!projectId) return;
    setOpen(false);
    // M18 target_type 4 态分流跳转
    if (item.target_type === "node") {
      router.push(`/projects/${projectId}/features/${item.target_id}`);
    } else if (item.target_type === "issue") {
      router.push(`/projects/${projectId}/issues`);
    } else {
      // dimension_record / competitor 没单独详情页，跳项目首页
      router.push(`/projects/${projectId}`);
    }
  };

  // 非项目上下文（/projects 列表 / /admin / /login 等）不渲染——M18 是 project-scoped
  if (!projectId) {
    return null;
  }

  return (
    <div ref={containerRef} className="relative w-80">
      <Search className="text-muted-foreground absolute top-1/2 left-3 z-10 h-4 w-4 -translate-y-1/2" />
      <Input
        className="pl-9"
        placeholder="搜索功能、维度、问题、竞品..."
        value={query}
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => {
          if (results.length > 0) setOpen(true);
        }}
      />

      {open && (
        <Card className="absolute top-full right-0 left-0 z-50 mt-1 overflow-hidden border shadow-lg">
          <div className="max-h-[360px] overflow-y-auto">
            {loading ? (
              <div className="text-muted-foreground px-4 py-3 text-sm">搜索中...</div>
            ) : (
              results.map((item) => (
                <button
                  key={item.target_id}
                  className="hover:bg-accent border-border/40 w-full border-b px-4 py-3 text-left transition-colors last:border-b-0"
                  onClick={() => handleResultClick(item)}
                >
                  <div className="mb-0.5 flex items-center gap-2">
                    <Badge variant="outline" className={cn("shrink-0 text-xs")}>
                      {targetTypeLabel[item.target_type] ?? item.target_type}
                    </Badge>
                    <span className="text-primary truncate text-sm font-medium">
                      {highlightKeyword(item.title, query)}
                    </span>
                  </div>
                  {item.breadcrumb && item.breadcrumb.length > 0 && (
                    <p className="text-muted-foreground truncate text-xs">
                      {item.breadcrumb.join(" → ")}
                    </p>
                  )}
                  {item.snippet && (
                    <p className="text-foreground/70 mt-1 line-clamp-1 text-xs">
                      {highlightKeyword(item.snippet, query)}
                    </p>
                  )}
                </button>
              ))
            )}
          </div>
          <button
            className="text-primary hover:bg-accent border-border w-full border-t px-4 py-2.5 text-center text-sm font-medium transition-colors"
            onClick={() => {
              setOpen(false);
              router.push(`/projects/${projectId}/search?q=${encodeURIComponent(query.trim())}`);
            }}
          >
            查看全部结果
          </button>
        </Card>
      )}
    </div>
  );
}
