"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bell, LogOut, Newspaper, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { NewsCard } from "@/components/news-card";
import { NewsForm } from "@/components/news-form";
import { listNews, type NewsResponse } from "@/actions/industry-news";
import { useAuth } from "@/contexts/auth-context";
import { isNextRedirectError } from "@/lib/errors";

/**
 * M14 行业动态全量页面（design §6 Page = web/src/app/industry-news/page.tsx）。
 *
 * 全局共享数据（design §1 灰区 2 + §9 GLOBAL DATA — NO TENANT FILTER）：
 *   - 不挂在 /projects/{pid}/ 下
 *   - 已登录即可读，已登录即可写（design §8）
 *
 * 顶部 nav 与 /projects, /teams 顶层 nav 范式一致（手动写 / 项目没有公共 layout）。
 * 列表：时间倒序分页（page_size=20 / design §7 default）
 * 过滤：tag query param（GIN 索引支持 / design §3）
 * 录入：右上角 + 按钮唤起 NewsForm
 */

const PAGE_SIZE = 20;

export default function IndustryNewsPage() {
  const router = useRouter();
  const { user, isLoading, logout } = useAuth();
  const [items, setItems] = useState<NewsResponse[] | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [tagFilter, setTagFilter] = useState("");
  const [appliedTag, setAppliedTag] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [loadError, setLoadError] = useState("");

  const loadList = useCallback((targetPage: number, tag: string) => {
    // setState 只放在 promise callback 里（react-hooks/set-state-in-effect 红线）
    listNews({ page: targetPage, pageSize: PAGE_SIZE, tag: tag || undefined })
      .then((data) => {
        setItems(data.items);
        setTotal(data.total);
        setLoadError("");
      })
      .catch((error) => {
        if (isNextRedirectError(error)) throw error;
        setItems([]);
        setTotal(0);
        setLoadError("加载行业动态失败");
      });
  }, []);

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    loadList(page, appliedTag);
  }, [user, isLoading, router, page, appliedTag, loadList]);

  const refresh = useCallback(() => {
    loadList(page, appliedTag);
  }, [loadList, page, appliedTag]);

  const handleApplyTag = () => {
    setAppliedTag(tagFilter.trim());
    setPage(1);
  };

  const handleClearTag = () => {
    setTagFilter("");
    setAppliedTag("");
    setPage(1);
  };

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  const userInitials = user?.name?.charAt(0) ?? "?";
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

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
              <Link href="/teams">
                <Button variant="ghost" size="sm">
                  团队
                </Button>
              </Link>
              <Button variant="secondary" size="sm" className="gap-2">
                <Newspaper className="h-4 w-4" />
                行业动态
              </Button>
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" aria-label="通知">
              <Bell className="h-5 w-5" />
            </Button>
            <Avatar className="h-8 w-8">
              <AvatarFallback>{userInitials}</AvatarFallback>
            </Avatar>
            <Button variant="ghost" size="icon" onClick={handleLogout} aria-label="退出登录">
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">行业动态</h1>
            <p className="mt-1 text-sm text-slate-500">
              全局共享的行业资讯，任何登录用户都能看到与录入
            </p>
          </div>
          <Button
            className="gap-2"
            onClick={() => setCreateOpen(true)}
            data-testid="news-create-btn"
          >
            <Plus className="h-4 w-4" />
            录入动态
          </Button>
        </div>

        {/* tag 过滤 */}
        <Card className="mb-4 p-4">
          <div className="flex items-center gap-3">
            <Input
              value={tagFilter}
              onChange={(e) => setTagFilter(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleApplyTag();
              }}
              placeholder="按标签过滤（输入后回车）"
              className="max-w-xs"
              aria-label="按标签过滤"
            />
            <Button variant="outline" size="sm" onClick={handleApplyTag}>
              过滤
            </Button>
            {appliedTag && (
              <Badge variant="secondary" className="gap-1">
                标签：{appliedTag}
                <button
                  type="button"
                  onClick={handleClearTag}
                  className="ml-1 inline-flex items-center"
                  aria-label="清除过滤"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            )}
            <span className="ml-auto text-sm text-slate-500">共 {total} 条</span>
          </div>
        </Card>

        {loadError && (
          <Card className="mb-4 border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {loadError}
          </Card>
        )}

        {/* 列表 */}
        {items === null ? (
          <Card className="p-8 text-center text-slate-500">加载中…</Card>
        ) : items.length === 0 ? (
          <Card className="p-12 text-center" data-testid="news-empty">
            <Newspaper className="mx-auto mb-4 h-12 w-12 text-slate-300" />
            <p className="mb-2 text-slate-600">
              {appliedTag ? "没有匹配该标签的动态" : "还没有任何行业动态"}
            </p>
            <p className="mb-6 text-sm text-slate-400">
              {appliedTag ? "试试其他标签或清除过滤" : "录入第一条让团队都看到"}
            </p>
            {!appliedTag && (
              <Button onClick={() => setCreateOpen(true)} className="gap-2">
                <Plus className="h-4 w-4" />
                录入动态
              </Button>
            )}
          </Card>
        ) : (
          <div className="space-y-3" data-testid="news-list">
            {items.map((news) => (
              <NewsCard key={news.id} news={news} onChanged={refresh} />
            ))}
          </div>
        )}

        {/* 分页 */}
        {items && items.length > 0 && totalPages > 1 && (
          <div className="mt-6 flex items-center justify-center gap-3">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              上一页
            </Button>
            <span className="text-sm text-slate-600">
              第 {page} / {totalPages} 页
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              下一页
            </Button>
          </div>
        )}
      </main>

      <NewsForm open={createOpen} onOpenChange={setCreateOpen} mode="create" onSuccess={refresh} />
    </div>
  );
}
