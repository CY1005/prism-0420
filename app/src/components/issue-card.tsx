"use client";

import { useState, useTransition } from "react";
import { Bug, Wrench, PenTool, Gauge, Plus, X, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

// ─── Category Config ────────────────────────────────────

type IssueCategory = "bug" | "tech_debt" | "design_flaw" | "performance";

const CATEGORY_CONFIG: Record<
  IssueCategory,
  { label: string; icon: LucideIcon; bgColor: string; textColor: string; iconBg: string }
> = {
  bug: {
    label: "Bug",
    icon: Bug,
    bgColor: "bg-red-100",
    textColor: "text-red-700",
    iconBg: "bg-red-100",
  },
  tech_debt: {
    label: "技术债",
    icon: Wrench,
    bgColor: "bg-orange-100",
    textColor: "text-orange-700",
    iconBg: "bg-orange-100",
  },
  design_flaw: {
    label: "设计缺陷",
    icon: PenTool,
    bgColor: "bg-purple-100",
    textColor: "text-purple-700",
    iconBg: "bg-purple-100",
  },
  performance: {
    label: "性能",
    icon: Gauge,
    bgColor: "bg-blue-100",
    textColor: "text-blue-700",
    iconBg: "bg-blue-100",
  },
};

// ADR-012: 问题按分类自动关联到对应维度
const CATEGORY_DIMENSION_MAP: Record<IssueCategory, string> = {
  bug: "test_analysis",
  tech_debt: "engineering_exp",
  design_flaw: "design_decision",
  performance: "tech_impl",
};

// ─── Types ──────────────────────────────────────────────

export type Issue = {
  id: string;
  projectId: string;
  nodeId: string | null;
  category: string;
  description: string;
  tags: string[] | null;
  createdAt: Date;
  updatedAt: Date;
};

// ─── Issue List Component ───────────────────────────────

interface IssueListProps {
  issues: Issue[];
  onAdd: () => void;
  onDelete: (issueId: string) => void;
  /** If provided, only show issues matching this dimension key */
  dimensionFilter?: string;
  /** If true, show the "添加问题" button */
  showAddButton?: boolean;
}

export function IssueList({
  issues,
  onAdd,
  onDelete,
  dimensionFilter,
  showAddButton = true,
}: IssueListProps) {
  const [tagFilter, setTagFilter] = useState<string | null>(null);

  // Filter by dimension if specified
  let filtered = dimensionFilter
    ? issues.filter((issue) => {
        const cat = issue.category as IssueCategory;
        return CATEGORY_DIMENSION_MAP[cat] === dimensionFilter;
      })
    : issues;

  // Filter by tag
  if (tagFilter) {
    filtered = filtered.filter((issue) => issue.tags?.includes(tagFilter));
  }

  // Collect all tags for the filter
  const allTags = Array.from(
    new Set(
      (dimensionFilter
        ? issues.filter((issue) => {
            const cat = issue.category as IssueCategory;
            return CATEGORY_DIMENSION_MAP[cat] === dimensionFilter;
          })
        : issues
      ).flatMap((issue) => issue.tags ?? []),
    ),
  );

  if (filtered.length === 0 && !showAddButton) return null;

  return (
    <div className="space-y-3">
      {/* Header with add button and tag filter */}
      <div className="flex items-center justify-between">
        <div className="flex flex-wrap items-center gap-2">
          {allTags.length > 0 && (
            <>
              <Badge
                variant={tagFilter === null ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => setTagFilter(null)}
              >
                全部
              </Badge>
              {allTags.map((tag) => (
                <Badge
                  key={tag}
                  variant={tagFilter === tag ? "default" : "outline"}
                  className="cursor-pointer text-xs"
                  onClick={() => setTagFilter(tagFilter === tag ? null : tag)}
                >
                  {tag}
                </Badge>
              ))}
            </>
          )}
        </div>
        {showAddButton && (
          <Button variant="outline" size="sm" onClick={onAdd}>
            <Plus className="mr-1 h-3.5 w-3.5" />
            添加问题
          </Button>
        )}
      </div>

      {/* Issue items */}
      {filtered.length === 0 ? (
        <p className="text-muted-foreground py-4 text-center text-sm">
          {tagFilter ? "没有匹配的问题" : "暂无问题"}
        </p>
      ) : (
        filtered.map((issue) => {
          const cat = issue.category as IssueCategory;
          const config = CATEGORY_CONFIG[cat];
          if (!config) return null;
          const Icon = config.icon;

          return (
            <div
              key={issue.id}
              className="border-border group flex items-start gap-3 rounded-md border p-3"
            >
              <div
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${config.iconBg} mt-0.5`}
              >
                <Icon className={`h-3.5 w-3.5 ${config.textColor}`} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex items-center gap-2">
                  <Badge
                    className={`${config.bgColor} ${config.textColor} hover:${config.bgColor} text-xs`}
                  >
                    {config.label}
                  </Badge>
                  <span className="truncate text-sm font-medium">{issue.description}</span>
                </div>
                {issue.tags && issue.tags.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {issue.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive h-7 w-7 shrink-0 p-0 opacity-0 transition-opacity group-hover:opacity-100"
                onClick={() => onDelete(issue.id)}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          );
        })
      )}
    </div>
  );
}

// ─── Add Issue Dialog ───────────────────────────────────

interface AddIssueDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: { category: string; description: string; tags: string[] }) => void;
}

export function AddIssueDialog({ open, onOpenChange, onSubmit }: AddIssueDialogProps) {
  const [category, setCategory] = useState<string>("bug");
  const [description, setDescription] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);

  const handleAddTag = () => {
    const trimmed = tagInput.trim();
    if (trimmed && !tags.includes(trimmed)) {
      setTags([...tags, trimmed]);
      setTagInput("");
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter((t) => t !== tag));
  };

  const handleSubmit = () => {
    if (!description.trim()) return;
    onSubmit({ category, description: description.trim(), tags });
    // Reset form
    setCategory("bug");
    setDescription("");
    setTags([]);
    setTagInput("");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>添加问题</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>分类</Label>
            <Select value={category} onValueChange={(val) => val && setCategory(val)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(CATEGORY_CONFIG).map(([key, config]) => {
                  const Icon = config.icon;
                  return (
                    <SelectItem key={key} value={key}>
                      <div className="flex items-center gap-2">
                        <Icon className={`h-3.5 w-3.5 ${config.textColor}`} />
                        {config.label}
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>描述</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="描述问题..."
              className="min-h-[80px]"
            />
          </div>

          <div className="space-y-2">
            <Label>标签</Label>
            <div className="flex gap-2">
              <Input
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                placeholder="输入标签后按回车"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddTag();
                  }
                }}
              />
              <Button
                variant="outline"
                size="sm"
                onClick={handleAddTag}
                disabled={!tagInput.trim()}
              >
                添加
              </Button>
            </div>
            {tags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="gap-1 text-xs">
                    {tag}
                    <X className="h-3 w-3 cursor-pointer" onClick={() => handleRemoveTag(tag)} />
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={!description.trim()}>
            保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Exports ────────────────────────────────────────────

export { CATEGORY_CONFIG, CATEGORY_DIMENSION_MAP };
export type { IssueCategory };
