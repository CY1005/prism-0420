"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { createNews, updateNews, type NewsResponse } from "@/actions/industry-news";
import { handleActionResult } from "@/lib/client-error";

/**
 * M14 行业动态录入/编辑表单（design §6 news-form.tsx + §7 NewsCreate/NewsUpdate schema）。
 *
 * 用法：
 *   <NewsForm open={open} onOpenChange={setOpen} mode="create" onSuccess={refresh} />
 *   <NewsForm open={open} onOpenChange={setOpen} mode="edit" news={existing} onSuccess={refresh} />
 *
 * tags 输入：逗号分隔（与 issue-card 风格一致 / max_length=50 单元素，后端 schema 兜底）
 * source_url 可空 + AnyHttpUrl 校验（design §14 E6 / zod url 校验前置 422 直拦）
 * published_date 可空 + YYYY-MM-DD（design §3）
 */

interface NewsFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit";
  news?: NewsResponse | null;
  onSuccess?: () => void;
}

// 内部 form：state 用 lazy initial value 从 props 初始化 / 通过 key 触发 remount 实现 reset。
// 避免在 useEffect 里同步 setState（react-hooks/set-state-in-effect / React 19 严格规约）。
interface NewsFormInnerProps {
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit";
  news?: NewsResponse | null;
  onSuccess?: () => void;
}

function NewsFormInner({ onOpenChange, mode, news, onSuccess }: NewsFormInnerProps) {
  const router = useRouter();
  const [title, setTitle] = useState(() => (mode === "edit" && news ? news.title : ""));
  const [summary, setSummary] = useState(() =>
    mode === "edit" && news ? (news.summary ?? "") : "",
  );
  const [sourceUrl, setSourceUrl] = useState(() =>
    mode === "edit" && news ? (news.source_url ?? "") : "",
  );
  const [publishedDate, setPublishedDate] = useState(() =>
    mode === "edit" && news ? (news.published_date ?? "") : "",
  );
  const [tagsRaw, setTagsRaw] = useState(() =>
    mode === "edit" && news ? (news.tags ?? []).join(", ") : "",
  );
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  const parseTags = (raw: string): string[] =>
    raw
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

  const handleSubmit = () => {
    if (!title.trim()) {
      setError("请输入标题");
      return;
    }
    setError("");

    const tags = parseTags(tagsRaw);

    startTransition(async () => {
      if (mode === "create") {
        const result = await createNews({
          title: title.trim(),
          summary: summary.trim() || undefined,
          sourceUrl: sourceUrl.trim() || undefined,
          publishedDate: publishedDate.trim() || undefined,
          tags: tags.length > 0 ? tags : undefined,
        });
        const handled = handleActionResult(result, router);
        if (handled.ok) {
          onOpenChange(false);
          onSuccess?.();
        } else if (!handled.autoHandled) {
          setError(handled.message);
        }
      } else {
        if (!news) return;
        const result = await updateNews({
          newsId: news.id,
          title: title.trim(),
          summary: summary.trim() || undefined,
          sourceUrl: sourceUrl.trim() || undefined,
          publishedDate: publishedDate.trim() || undefined,
          tags,
        });
        const handled = handleActionResult(result, router);
        if (handled.ok) {
          onOpenChange(false);
          onSuccess?.();
        } else if (!handled.autoHandled) {
          setError(handled.message);
        }
      }
    });
  };

  return (
    <DialogContent className="max-w-2xl">
      <DialogHeader>
        <DialogTitle>{mode === "create" ? "录入行业动态" : "编辑行业动态"}</DialogTitle>
      </DialogHeader>

      <div className="space-y-4 py-2">
        <div className="space-y-2">
          <Label htmlFor="news-title">
            标题 <span className="text-red-500">*</span>
          </Label>
          <Input
            id="news-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="例如：AI 监管新规发布"
            maxLength={200}
            disabled={isPending}
            autoFocus
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="news-summary">摘要</Label>
          <Textarea
            id="news-summary"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            placeholder="简要描述这条动态（可选）"
            maxLength={5000}
            rows={4}
            disabled={isPending}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="news-source-url">来源链接</Label>
            <Input
              id="news-source-url"
              type="url"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              placeholder="https://..."
              disabled={isPending}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="news-published-date">发布日期</Label>
            <Input
              id="news-published-date"
              type="date"
              value={publishedDate}
              onChange={(e) => setPublishedDate(e.target.value)}
              disabled={isPending}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="news-tags">标签（逗号分隔）</Label>
          <Input
            id="news-tags"
            value={tagsRaw}
            onChange={(e) => setTagsRaw(e.target.value)}
            placeholder="AI, 监管, 产品"
            disabled={isPending}
          />
          <p className="text-xs text-slate-500">单个标签最多 50 字符，最多 20 个标签</p>
        </div>

        {error && (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
          取消
        </Button>
        <Button onClick={handleSubmit} disabled={isPending || !title.trim()}>
          {isPending ? "保存中…" : mode === "create" ? "创建" : "保存"}
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}

export function NewsForm({ open, onOpenChange, mode, news, onSuccess }: NewsFormProps) {
  // 用 key 触发 remount → 每次 open 或切换 news 时 inner state 自动复位（lazy initial value）
  const key = open ? `${mode}-${news?.id ?? "new"}` : "closed";
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {open && (
        <NewsFormInner
          key={key}
          onOpenChange={onOpenChange}
          mode={mode}
          news={news}
          onSuccess={onSuccess}
        />
      )}
    </Dialog>
  );
}
