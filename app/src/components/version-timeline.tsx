"use client";

import { useState } from "react";
import {
  Plus,
  Pencil,
  Archive,
  Split,
  Merge,
  ArrowRightLeft,
  ChevronDown,
  History,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
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
import { cn } from "@/lib/utils";

// ─── Change Type Config ──────────────────────────────

const changeTypeConfig: Record<
  string,
  { label: string; color: string; bgColor: string; icon: typeof Plus }
> = {
  added: { label: "新增", color: "text-green-700", bgColor: "bg-green-100", icon: Plus },
  modified: { label: "修改", color: "text-blue-700", bgColor: "bg-blue-100", icon: Pencil },
  deprecated: { label: "废弃", color: "text-gray-600", bgColor: "bg-gray-100", icon: Archive },
  split: { label: "拆分", color: "text-orange-700", bgColor: "bg-orange-100", icon: Split },
  merged: { label: "合并", color: "text-purple-700", bgColor: "bg-purple-100", icon: Merge },
  migrated: { label: "迁移", color: "text-cyan-700", bgColor: "bg-cyan-100", icon: ArrowRightLeft },
};

const changeTypes = Object.keys(changeTypeConfig);

export interface VersionRecord {
  id: string;
  versionLabel: string;
  summary: string;
  details?: string | null;
  changeType: string;
  isCurrent: boolean;
  snapshotData?: Record<string, unknown>[] | null;
  createdAt: string | Date;
}

interface VersionTimelineProps {
  versions: VersionRecord[];
  versionMode?: "release" | "continuous";
  onCreateVersion?: (data: {
    versionLabel: string;
    summary: string;
    changeType: string;
    details?: string;
  }) => void;
}

function ChangeTypeBadge({ changeType }: { changeType: string }) {
  const config = changeTypeConfig[changeType] ?? changeTypeConfig.added;
  const Icon = config.icon;
  return (
    <Badge className={cn("gap-1 text-xs", config.bgColor, config.color, `hover:${config.bgColor}`)}>
      <Icon className="h-3 w-3" />
      {config.label}
    </Badge>
  );
}

export function VersionTimeline({
  versions,
  versionMode = "release",
  onCreateVersion,
}: VersionTimelineProps) {
  const [expandedVersions, setExpandedVersions] = useState<Set<string>>(new Set());
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newVersion, setNewVersion] = useState({
    versionLabel: "",
    summary: "",
    changeType: "added",
    details: "",
  });

  const toggleVersion = (id: string) => {
    setExpandedVersions((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSubmit = () => {
    if (!newVersion.versionLabel.trim() || !newVersion.summary.trim()) return;
    onCreateVersion?.({
      versionLabel: newVersion.versionLabel.trim(),
      summary: newVersion.summary.trim(),
      changeType: newVersion.changeType,
      details: newVersion.details.trim() || undefined,
    });
    setShowAddDialog(false);
    setNewVersion({ versionLabel: "", summary: "", changeType: "added", details: "" });
  };

  return (
    <div className="mt-8 border-t pt-6">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="text-primary h-5 w-5" />
          <h2 className="text-lg font-semibold">版本演进</h2>
        </div>
        {onCreateVersion && (
          <Button variant="outline" size="sm" onClick={() => setShowAddDialog(true)}>
            <Plus className="mr-1 h-4 w-4" />
            添加版本记录
          </Button>
        )}
      </div>

      {versions.length === 0 ? (
        <div className="text-muted-foreground py-8 text-center">
          <History className="mx-auto mb-2 h-10 w-10 opacity-40" />
          <p className="text-sm">暂无版本记录</p>
        </div>
      ) : (
        <div className="relative space-y-0">
          {versions.map((v, index) => {
            const isExpanded = expandedVersions.has(v.id);
            const isLast = index === versions.length - 1;
            const config = changeTypeConfig[v.changeType] ?? changeTypeConfig.added;

            return (
              <div key={v.id} className="relative flex gap-4">
                {/* Timeline line */}
                <div className="relative flex flex-col items-center">
                  <div
                    className={cn(
                      "z-10 h-3 w-3 shrink-0 rounded-full border-2",
                      v.isCurrent
                        ? "border-primary bg-primary"
                        : "border-muted-foreground/40 bg-background",
                    )}
                  />
                  {!isLast && <div className="bg-border w-0.5 flex-1" />}
                </div>

                {/* Content */}
                <div className="flex-1 pb-6">
                  <Collapsible
                    open={isExpanded}
                    onOpenChange={() => (v.snapshotData || v.details) && toggleVersion(v.id)}
                  >
                    <div className="flex flex-wrap items-start gap-2">
                      <span
                        className={cn(
                          "font-mono text-sm font-medium",
                          v.isCurrent ? "text-primary" : "text-muted-foreground",
                        )}
                      >
                        {v.versionLabel}
                      </span>
                      <ChangeTypeBadge changeType={v.changeType} />
                      {v.isCurrent && <Badge className="text-xs">当前版本</Badge>}
                      {(v.snapshotData || v.details) && (
                        <CollapsibleTrigger className="hover:bg-accent inline-flex h-6 w-6 items-center justify-center rounded-md">
                          <ChevronDown
                            className={cn(
                              "text-muted-foreground h-3 w-3 transition-transform",
                              isExpanded && "rotate-180",
                            )}
                          />
                        </CollapsibleTrigger>
                      )}
                    </div>
                    <p className="text-muted-foreground mt-1 text-sm">{v.summary}</p>
                    <CollapsibleContent>
                      {v.details && (
                        <p className="text-muted-foreground/80 bg-muted/50 mt-2 rounded-md p-3 text-sm">
                          {v.details}
                        </p>
                      )}
                      {v.snapshotData && v.snapshotData.length > 0 && (
                        <div className="bg-muted/30 mt-2 rounded-md border p-3">
                          <p className="text-muted-foreground mb-2 text-xs font-medium">维度快照</p>
                          <div className="space-y-1">
                            {v.snapshotData.map((snap, i) => (
                              <div key={i} className="text-muted-foreground text-xs">
                                <span className="font-medium">
                                  {(snap as Record<string, unknown>).dimensionName as string}:
                                </span>{" "}
                                {JSON.stringify((snap as Record<string, unknown>).content)}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </CollapsibleContent>
                  </Collapsible>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Version Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加版本记录</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>版本标签</Label>
              <Input
                value={newVersion.versionLabel}
                onChange={(e) => setNewVersion((p) => ({ ...p, versionLabel: e.target.value }))}
                placeholder={versionMode === "continuous" ? "例如: 2026-04-12" : "例如: v3.9.3"}
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label>变更类型</Label>
              <Select
                value={newVersion.changeType}
                onValueChange={(v) => {
                  if (v) setNewVersion((p) => ({ ...p, changeType: v }));
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {changeTypes.map((ct) => (
                    <SelectItem key={ct} value={ct}>
                      {changeTypeConfig[ct].label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>摘要</Label>
              <Input
                value={newVersion.summary}
                onChange={(e) => setNewVersion((p) => ({ ...p, summary: e.target.value }))}
                placeholder="简要描述本次变更"
              />
            </div>
            <div className="space-y-2">
              <Label>详细说明（可选）</Label>
              <textarea
                className="bg-background focus-visible:ring-ring flex min-h-[80px] w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:outline-none"
                value={newVersion.details}
                onChange={(e) => setNewVersion((p) => ({ ...p, details: e.target.value }))}
                placeholder="补充详细信息..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              取消
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={!newVersion.versionLabel.trim() || !newVersion.summary.trim()}
            >
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
