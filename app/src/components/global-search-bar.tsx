"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { globalSearch } from "@/actions/search";
import { type SearchResultItem } from "@/services/search";
import { cn } from "@/lib/utils";

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
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    const result = await globalSearch(q.trim(), { limit: 5 });
    setLoading(false);
    if (result.success) {
      setResults(result.data.results);
      setOpen(result.data.results.length > 0);
    } else {
      setResults([]);
      setOpen(false);
    }
  }, []);

  const handleChange = (value: string) => {
    setQuery(value);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSearch(value), 300);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && query.trim()) {
      setOpen(false);
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
    if (e.key === "Escape") {
      setOpen(false);
    }
  };

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Cleanup timer
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleResultClick = (item: SearchResultItem) => {
    setOpen(false);
    if (item.project_id && item.node_id) {
      router.push(`/projects/${item.project_id}/features/${item.node_id}`);
    } else if (item.project_id) {
      router.push(`/projects/${item.project_id}`);
    }
  };

  return (
    <div ref={containerRef} className="relative w-80">
      <Search className="text-muted-foreground absolute top-1/2 left-3 z-10 h-4 w-4 -translate-y-1/2" />
      <Input
        className="pl-9"
        placeholder="搜索功能、模块、问题..."
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
                  key={item.id}
                  className="hover:bg-accent border-border/40 w-full border-b px-4 py-3 text-left transition-colors last:border-b-0"
                  onClick={() => handleResultClick(item)}
                >
                  <div className="mb-0.5 flex items-center gap-2">
                    {item.project_name && (
                      <Badge
                        variant="outline"
                        className={cn("shrink-0 text-xs", getProjectBadgeClass(item.project_name))}
                      >
                        {item.project_name}
                      </Badge>
                    )}
                    <span className="text-primary truncate text-sm font-medium">
                      {highlightKeyword(item.title, query)}
                    </span>
                  </div>
                  {item.breadcrumb && item.breadcrumb.length > 0 && (
                    <p className="text-muted-foreground truncate text-xs">
                      {item.breadcrumb.join(" → ")}
                    </p>
                  )}
                  {item.content_snippet && (
                    <p className="text-foreground/70 mt-1 line-clamp-1 text-xs">
                      {highlightKeyword(item.content_snippet, query)}
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
              router.push(`/search?q=${encodeURIComponent(query.trim())}`);
            }}
          >
            查看全部结果
          </button>
        </Card>
      )}
    </div>
  );
}
