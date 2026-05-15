"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Calendar, ExternalLink, Link2, Pencil, Trash2, User } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { NewsForm } from "@/components/news-form";
import { NodeLinkPicker } from "@/components/node-link-picker";
import { deleteNews, type NewsResponse } from "@/actions/industry-news";
import { handleActionResult } from "@/lib/client-error";

/**
 * M14 行业动态卡片（design §6 news-card.tsx）。
 *
 * 展示一条动态：标题 / 摘要 / 发布日期 / 来源链接 / 录入者 / tags + 已关联功能项。
 * 操作：编辑（NewsForm） / 删除（确认 dialog） / 关联功能项（NodeLinkPicker）。
 *
 * 当前用户 != 录入者 时 service 层会 403（design §8 _check_news_owner_or_admin）；
 * 前端不提前隐藏按钮 — 因为 admin 可以删/改任意 news，前端拿不到 admin role；
 * 用户点击后由 error 提示展示（与 issue-card 同处理范式）。
 */

interface NewsCardProps {
  news: NewsResponse;
  onChanged?: () => void;
}

export function NewsCard({ news, onChanged }: NewsCardProps) {
  const router = useRouter();
  const [editOpen, setEditOpen] = useState(false);
  const [linkOpen, setLinkOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [isPending, startTransition] = useTransition();

  const linkedNodes = news.linked_nodes ?? [];

  const handleDelete = () => {
    setDeleteError("");
    startTransition(async () => {
      const result = await deleteNews(news.id);
      const handled = handleActionResult(result, router);
      if (handled.ok) {
        setDeleteOpen(false);
        onChanged?.();
      } else if (!handled.autoHandled) {
        setDeleteError(handled.message);
      }
    });
  };

  const formattedDate = news.published_date
    ? new Date(news.published_date).toLocaleDateString("zh-CN")
    : null;
  const createdAt = new Date(news.created_at).toLocaleDateString("zh-CN");

  return (
    <>
      <Card className="p-5" data-testid="news-card" data-news-id={news.id}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="line-clamp-2 font-semibold text-slate-900" data-testid="news-title">
              {news.title}
            </h3>
            {news.summary && (
              <p className="mt-2 line-clamp-3 text-sm text-slate-600">{news.summary}</p>
            )}
          </div>
          <div className="flex shrink-0 gap-1">
            <Button
              variant="ghost"
              size="icon"
              aria-label="关联功能项"
              onClick={() => setLinkOpen(true)}
              className="h-8 w-8"
            >
              <Link2 className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              aria-label="编辑动态"
              onClick={() => setEditOpen(true)}
              className="h-8 w-8"
            >
              <Pencil className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              aria-label="删除动态"
              onClick={() => setDeleteOpen(true)}
              className="h-8 w-8 text-red-500 hover:bg-red-50 hover:text-red-600"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {(news.tags?.length ?? 0) > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {news.tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}

        {linkedNodes.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5" data-testid="news-linked-nodes">
            {linkedNodes.map((n) => (
              <Badge
                key={n.node_id}
                variant="outline"
                className="bg-blue-50 text-xs text-blue-700"
                data-node-id={n.node_id}
              >
                <Link2 className="mr-1 h-3 w-3" />
                {n.node_name}
              </Badge>
            ))}
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
          {formattedDate && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              发布 {formattedDate}
            </span>
          )}
          <span className="flex items-center gap-1">
            <User className="h-3 w-3" />
            {news.created_by_name || "未知录入者"}
          </span>
          <span>录入 {createdAt}</span>
          {news.source_url && (
            <a
              href={news.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="ml-auto flex items-center gap-1 text-blue-600 hover:text-blue-700"
            >
              <ExternalLink className="h-3 w-3" />
              来源
            </a>
          )}
        </div>
      </Card>

      <NewsForm
        open={editOpen}
        onOpenChange={setEditOpen}
        mode="edit"
        news={news}
        onSuccess={onChanged}
      />
      <NodeLinkPicker
        newsId={news.id}
        linkedNodes={linkedNodes}
        open={linkOpen}
        onOpenChange={setLinkOpen}
        onChanged={onChanged}
      />

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>确定要删除「{news.title}」吗？此操作不可恢复。</DialogDescription>
          </DialogHeader>
          {deleteError && (
            <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
              {deleteError}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)} disabled={isPending}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={isPending}>
              {isPending ? "删除中…" : "删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
