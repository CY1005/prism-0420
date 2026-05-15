"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { ChevronRight, Folder, FileText, Link2, X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getProjects, type Project } from "@/actions/projects";
import { getProjectTree } from "@/actions/nodes";
import { linkNewsToNode, unlinkNewsFromNode } from "@/actions/industry-news";
import { handleActionResult } from "@/lib/client-error";
import type { components } from "@/types/api";

/**
 * M14 关联功能项 picker（design §6 node-link-picker.tsx）。
 *
 * 行为：
 *   1) 用户从已加入项目列表中选择一个 project
 *   2) 加载该 project 的 node tree（递归折叠）
 *   3) 点击节点 → POST /api/news/{news_id}/links → 关闭 dialog + 刷新
 *
 * 跨项目关联是预期行为（design §1 灰区 2 + tests.md T4 — 全局动态可关联任意 node）。
 * 已关联节点列表也在本组件里展示并提供解除按钮（design §8 link/unlink 已登录即可）。
 */

type NodeRef = components["schemas"]["NodeRef"];

interface FlatNode {
  id: string;
  name: string;
  type: "folder" | "file";
  depth: number;
}

interface NodeLinkPickerProps {
  newsId: string;
  linkedNodes: NodeRef[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onChanged?: () => void;
}

// 把嵌套 TreeNode 平展为带 depth 的列表（picker 用扁平列表 + 缩进展示）
interface ProjectTreeNode {
  id: string;
  name: string;
  type: "folder" | "file";
  children: ProjectTreeNode[];
}

function flattenTree(nodes: ProjectTreeNode[], depth = 0, acc: FlatNode[] = []): FlatNode[] {
  for (const n of nodes) {
    acc.push({ id: n.id, name: n.name, type: n.type, depth });
    if (n.children?.length) {
      flattenTree(n.children, depth + 1, acc);
    }
  }
  return acc;
}

interface NodeLinkPickerInnerProps {
  newsId: string;
  linkedNodes: NodeRef[];
  onOpenChange: (open: boolean) => void;
  onChanged?: () => void;
}

function NodeLinkPickerInner({
  newsId,
  linkedNodes,
  onOpenChange,
  onChanged,
}: NodeLinkPickerInnerProps) {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [nodes, setNodes] = useState<FlatNode[] | null>(null);
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();
  const linkedIds = new Set(linkedNodes.map((n) => n.node_id));

  // 拉项目列表（mount 即拉 / 由 NodeLinkPicker 用 key 控制 remount）
  useEffect(() => {
    getProjects()
      .then(setProjects)
      .catch(() => setProjects([]));
  }, []);

  // 选定 project → 加载 tree（setState 只在 promise callback 里，effect body 不同步 setState）
  useEffect(() => {
    if (!selectedProjectId) return;
    let cancelled = false;
    getProjectTree(selectedProjectId)
      .then((tree) => {
        if (cancelled) return;
        const flat = flattenTree(tree as ProjectTreeNode[]);
        setNodes(flat);
      })
      .catch(() => {
        if (cancelled) return;
        setNodes([]);
        setError("加载节点树失败");
      });
    return () => {
      cancelled = true;
    };
  }, [selectedProjectId]);

  const handleSelectProject = (v: string) => {
    setSelectedProjectId(v);
    setNodes(null); // event handler 里 setState 合规
  };

  const handleLink = (nodeId: string) => {
    setError("");
    startTransition(async () => {
      const result = await linkNewsToNode({ newsId, nodeId });
      const handled = handleActionResult(result, router);
      if (handled.ok) {
        onChanged?.();
        onOpenChange(false);
      } else if (!handled.autoHandled) {
        setError(handled.message);
      }
    });
  };

  const handleUnlink = (nodeId: string) => {
    setError("");
    startTransition(async () => {
      const result = await unlinkNewsFromNode(newsId, nodeId);
      const handled = handleActionResult(result, router);
      if (handled.ok) {
        onChanged?.();
      } else if (!handled.autoHandled) {
        setError(handled.message);
      }
    });
  };

  return (
    <DialogContent className="max-w-xl">
      <DialogHeader>
        <DialogTitle>关联功能项</DialogTitle>
      </DialogHeader>

      <div className="space-y-4">
        {/* 已关联节点 */}
        {linkedNodes.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-slate-700">已关联（{linkedNodes.length}）</p>
            <ul className="space-y-1">
              {linkedNodes.map((n) => (
                <li
                  key={n.node_id}
                  className="flex items-center justify-between rounded bg-slate-50 px-3 py-2 text-sm"
                >
                  <span className="flex items-center gap-2">
                    <Link2 className="h-3.5 w-3.5 text-slate-400" />
                    <span className="text-slate-700">{n.node_name}</span>
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={isPending}
                    onClick={() => handleUnlink(n.node_id)}
                    aria-label="解除关联"
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* project 选择 */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-700">选择项目</p>
          {projects === null ? (
            <p className="text-sm text-slate-500">加载中…</p>
          ) : projects.length === 0 ? (
            <p className="text-sm text-slate-500">你还没有加入任何项目</p>
          ) : (
            <Select value={selectedProjectId} onValueChange={(v) => handleSelectProject(v ?? "")}>
              <SelectTrigger aria-label="选择项目">
                <SelectValue placeholder="选择一个项目" />
              </SelectTrigger>
              <SelectContent>
                {projects.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>

        {/* node tree */}
        {selectedProjectId && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-slate-700">选择功能项</p>
            {nodes === null ? (
              <p className="text-sm text-slate-500">加载中…</p>
            ) : nodes.length === 0 ? (
              <p className="text-sm text-slate-500">该项目暂无功能项</p>
            ) : (
              <ul className="max-h-72 space-y-0.5 overflow-y-auto rounded border border-slate-200 p-2">
                {nodes.map((n) => {
                  const isLinked = linkedIds.has(n.id);
                  const Icon = n.type === "folder" ? Folder : FileText;
                  return (
                    <li key={n.id}>
                      <button
                        type="button"
                        disabled={isPending || isLinked}
                        onClick={() => handleLink(n.id)}
                        className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                        style={{ paddingLeft: `${n.depth * 16 + 8}px` }}
                        aria-label={`关联到 ${n.name}`}
                      >
                        <ChevronRight className="h-3 w-3 shrink-0 text-slate-300" aria-hidden />
                        <Icon className="h-3.5 w-3.5 shrink-0 text-slate-400" aria-hidden />
                        <span className="truncate text-slate-700">{n.name}</span>
                        {isLinked && (
                          <span className="ml-auto shrink-0 text-xs text-slate-400">已关联</span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}

        {error && (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
          完成
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}

export function NodeLinkPicker({
  newsId,
  linkedNodes,
  open,
  onOpenChange,
  onChanged,
}: NodeLinkPickerProps) {
  // 用 key 触发 remount → 每次重新打开都 reset inner state（lazy init + no setState in effect）
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {open && (
        <NodeLinkPickerInner
          key={`${newsId}-${linkedNodes.length}`}
          newsId={newsId}
          linkedNodes={linkedNodes}
          onOpenChange={onOpenChange}
          onChanged={onChanged}
        />
      )}
    </Dialog>
  );
}
