"use client";

import { useState } from "react";
import { Plus, X, Pencil, Trash2, Building, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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

// ─── Types ──────────────────────────────────────────────
// Phase 2.3 cleanup A: actions 层做 snake → camel adapter，nested form 单点维护。

import type { Competitor } from "@/actions/competitors";
import type { CompetitorReference } from "@/actions/competitor-references";
export type { Competitor, CompetitorReference };

// ─── Reference List ─────────────────────────────────────

interface CompetitorReferenceListProps {
  references: CompetitorReference[];
  competitors: Competitor[];
  onAdd: () => void;
  onEdit: (ref: CompetitorReference) => void;
  onDelete: (refId: string) => void;
}

export function CompetitorReferenceList({
  references,
  competitors,
  onAdd,
  onEdit,
  onDelete,
}: CompetitorReferenceListProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-medium">竞品参考</h3>
        <Button variant="outline" size="sm" onClick={onAdd}>
          <Plus className="mr-1 h-3.5 w-3.5" />
          添加竞品参考
        </Button>
      </div>

      {references.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-md border border-dashed py-8 text-center">
          <Building className="text-muted-foreground/40 mb-2 h-10 w-10" />
          <p className="text-muted-foreground text-sm">暂无竞品参考，点击添加</p>
        </div>
      ) : (
        <div className="space-y-4">
          {references.map((ref) => (
            <div key={ref.reference.id} className="border-border group rounded-md border p-4">
              <div className="mb-2 flex items-center gap-2">
                <span className="text-sm font-medium">{ref.competitor.name}</span>
                {ref.reference.version && (
                  <Badge variant="outline" className="text-xs">
                    {ref.reference.version}
                  </Badge>
                )}
                {ref.competitor.website && (
                  <a
                    href={ref.competitor.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
                <div className="flex-1" />
                <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => onEdit(ref)}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive h-7 w-7 p-0"
                    onClick={() => onDelete(ref.reference.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>

              {ref.reference.featureCoverage && (
                <p className="text-muted-foreground mb-3 text-sm">
                  {ref.reference.featureCoverage}
                </p>
              )}

              {ref.reference.technicalApproach && (
                <p className="text-muted-foreground mb-3 text-sm">
                  <span className="text-foreground text-xs font-medium">技术方案：</span>
                  {ref.reference.technicalApproach}
                </p>
              )}

              {ref.reference.prosAndCons &&
                ((ref.reference.prosAndCons.pros?.length ?? 0) > 0 ||
                  (ref.reference.prosAndCons.cons?.length ?? 0) > 0) && (
                  <div className="grid grid-cols-2 gap-3">
                    {(ref.reference.prosAndCons.pros?.length ?? 0) > 0 && (
                      <div className="rounded-md bg-green-50/50 p-3">
                        <h5 className="mb-1 text-xs font-medium text-green-700">优势</h5>
                        <ul className="text-muted-foreground space-y-0.5 text-xs">
                          {ref.reference.prosAndCons.pros.map((pro, i) => (
                            <li key={i}>- {pro}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {(ref.reference.prosAndCons.cons?.length ?? 0) > 0 && (
                      <div className="rounded-md bg-red-50/50 p-3">
                        <h5 className="mb-1 text-xs font-medium text-red-700">劣势</h5>
                        <ul className="text-muted-foreground space-y-0.5 text-xs">
                          {ref.reference.prosAndCons.cons.map((con, i) => (
                            <li key={i}>- {con}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Add/Edit Reference Dialog ──────────────────────────

interface AddReferenceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  competitors: Competitor[];
  onCreateCompetitor: (data: {
    name: string;
    website?: string;
    description?: string;
  }) => Promise<string | null>;
  onSubmit: (data: {
    competitorId: string;
    version?: string;
    featureCoverage?: string;
    technicalApproach?: string;
    prosAndCons?: { pros: string[]; cons: string[] };
  }) => void;
  /** Pre-fill for editing */
  editingRef?: CompetitorReference | null;
}

export function AddReferenceDialog({
  open,
  onOpenChange,
  competitors,
  onCreateCompetitor,
  onSubmit,
  editingRef,
}: AddReferenceDialogProps) {
  const [competitorId, setCompetitorId] = useState(editingRef?.reference.competitorId ?? "");
  const [version, setVersion] = useState(editingRef?.reference.version ?? "");
  const [featureCoverage, setFeatureCoverage] = useState(
    editingRef?.reference.featureCoverage ?? "",
  );
  const [technicalApproach, setTechnicalApproach] = useState(
    editingRef?.reference.technicalApproach ?? "",
  );
  const [pros, setPros] = useState<string[]>(editingRef?.reference.prosAndCons?.pros ?? []);
  const [cons, setCons] = useState<string[]>(editingRef?.reference.prosAndCons?.cons ?? []);
  const [proInput, setProInput] = useState("");
  const [conInput, setConInput] = useState("");

  // New competitor inline creation
  const [showNewCompetitor, setShowNewCompetitor] = useState(false);
  const [newName, setNewName] = useState("");
  const [newWebsite, setNewWebsite] = useState("");

  // Reset form when dialog opens with different data
  const resetForm = () => {
    setCompetitorId(editingRef?.reference.competitorId ?? "");
    setVersion(editingRef?.reference.version ?? "");
    setFeatureCoverage(editingRef?.reference.featureCoverage ?? "");
    setTechnicalApproach(editingRef?.reference.technicalApproach ?? "");
    setPros(editingRef?.reference.prosAndCons?.pros ?? []);
    setCons(editingRef?.reference.prosAndCons?.cons ?? []);
    setProInput("");
    setConInput("");
    setShowNewCompetitor(false);
    setNewName("");
    setNewWebsite("");
  };

  const handleSubmit = () => {
    if (!competitorId) return;
    onSubmit({
      competitorId,
      version: version || undefined,
      featureCoverage: featureCoverage || undefined,
      technicalApproach: technicalApproach || undefined,
      prosAndCons: pros.length > 0 || cons.length > 0 ? { pros, cons } : undefined,
    });
    resetForm();
    onOpenChange(false);
  };

  const handleCreateCompetitor = async () => {
    if (!newName.trim()) return;
    const id = await onCreateCompetitor({
      name: newName.trim(),
      website: newWebsite.trim() || undefined,
    });
    if (id) {
      setCompetitorId(id);
      setShowNewCompetitor(false);
      setNewName("");
      setNewWebsite("");
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(val) => {
        if (!val) resetForm();
        onOpenChange(val);
      }}
    >
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle>{editingRef ? "编辑竞品参考" : "添加竞品参考"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          {/* Competitor selection */}
          <div className="space-y-2">
            <Label>竞品</Label>
            {!showNewCompetitor ? (
              <div className="flex gap-2">
                <Select value={competitorId} onValueChange={(val) => val && setCompetitorId(val)}>
                  <SelectTrigger className="flex-1">
                    <SelectValue placeholder="选择竞品..." />
                  </SelectTrigger>
                  <SelectContent>
                    {competitors.map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        {c.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {!editingRef && (
                  <Button variant="outline" size="sm" onClick={() => setShowNewCompetitor(true)}>
                    新建
                  </Button>
                )}
              </div>
            ) : (
              <div className="space-y-2 rounded-md border p-3">
                <Input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="竞品名称"
                />
                <Input
                  value={newWebsite}
                  onChange={(e) => setNewWebsite(e.target.value)}
                  placeholder="网站（可选）"
                />
                <div className="flex gap-2">
                  <Button size="sm" onClick={handleCreateCompetitor} disabled={!newName.trim()}>
                    创建
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setShowNewCompetitor(false)}>
                    取消
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* Version */}
          <div className="space-y-2">
            <Label>竞品版本（可选）</Label>
            <Input
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              placeholder="如 v2.x"
            />
          </div>

          {/* Feature coverage */}
          <div className="space-y-2">
            <Label>功能覆盖度</Label>
            <Textarea
              value={featureCoverage}
              onChange={(e) => setFeatureCoverage(e.target.value)}
              placeholder="描述该竞品对此功能的覆盖情况..."
              className="min-h-[60px]"
            />
          </div>

          {/* Technical approach */}
          <div className="space-y-2">
            <Label>技术方案</Label>
            <Textarea
              value={technicalApproach}
              onChange={(e) => setTechnicalApproach(e.target.value)}
              placeholder="描述该竞品的技术实现方案..."
              className="min-h-[60px]"
            />
          </div>

          {/* Pros */}
          <div className="space-y-2">
            <Label>优势</Label>
            <div className="flex gap-2">
              <Input
                value={proInput}
                onChange={(e) => setProInput(e.target.value)}
                placeholder="输入优势后按回车"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    if (proInput.trim()) {
                      setPros([...pros, proInput.trim()]);
                      setProInput("");
                    }
                  }
                }}
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (proInput.trim()) {
                    setPros([...pros, proInput.trim()]);
                    setProInput("");
                  }
                }}
                disabled={!proInput.trim()}
              >
                添加
              </Button>
            </div>
            {pros.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {pros.map((p, i) => (
                  <Badge
                    key={i}
                    variant="secondary"
                    className="gap-1 bg-green-50 text-xs text-green-700"
                  >
                    {p}
                    <X
                      className="h-3 w-3 cursor-pointer"
                      onClick={() => setPros(pros.filter((_, j) => j !== i))}
                    />
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {/* Cons */}
          <div className="space-y-2">
            <Label>劣势</Label>
            <div className="flex gap-2">
              <Input
                value={conInput}
                onChange={(e) => setConInput(e.target.value)}
                placeholder="输入劣势后按回车"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    if (conInput.trim()) {
                      setCons([...cons, conInput.trim()]);
                      setConInput("");
                    }
                  }
                }}
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (conInput.trim()) {
                    setCons([...cons, conInput.trim()]);
                    setConInput("");
                  }
                }}
                disabled={!conInput.trim()}
              >
                添加
              </Button>
            </div>
            {cons.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {cons.map((c, i) => (
                  <Badge
                    key={i}
                    variant="secondary"
                    className="gap-1 bg-red-50 text-xs text-red-700"
                  >
                    {c}
                    <X
                      className="h-3 w-3 cursor-pointer"
                      onClick={() => setCons(cons.filter((_, j) => j !== i))}
                    />
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => {
              resetForm();
              onOpenChange(false);
            }}
          >
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={!competitorId}>
            保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Competitor Management (Settings) ───────────────────

interface CompetitorManagementProps {
  competitors: Competitor[];
  onCreateCompetitor: (data: { name: string; website?: string; description?: string }) => void;
  onUpdateCompetitor: (
    id: string,
    data: { name?: string; website?: string; description?: string },
  ) => void;
  onDeleteCompetitor: (id: string) => void;
  canAdmin: boolean;
}

export function CompetitorManagement({
  competitors,
  onCreateCompetitor,
  onUpdateCompetitor,
  onDeleteCompetitor,
  canAdmin,
}: CompetitorManagementProps) {
  const [addDialog, setAddDialog] = useState(false);
  const [editDialog, setEditDialog] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formName, setFormName] = useState("");
  const [formWebsite, setFormWebsite] = useState("");
  const [formDescription, setFormDescription] = useState("");

  const openCreate = () => {
    setFormName("");
    setFormWebsite("");
    setFormDescription("");
    setAddDialog(true);
  };

  const openEdit = (c: Competitor) => {
    setEditingId(c.id);
    setFormName(c.name);
    setFormWebsite(c.website ?? "");
    setFormDescription(c.description ?? "");
    setEditDialog(true);
  };

  const handleCreate = () => {
    if (!formName.trim()) return;
    onCreateCompetitor({
      name: formName.trim(),
      website: formWebsite.trim() || undefined,
      description: formDescription.trim() || undefined,
    });
    setAddDialog(false);
  };

  const handleUpdate = () => {
    if (!editingId || !formName.trim()) return;
    onUpdateCompetitor(editingId, {
      name: formName.trim(),
      website: formWebsite.trim() || undefined,
      description: formDescription.trim() || undefined,
    });
    setEditDialog(false);
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">竞品管理</h2>
          <p className="text-muted-foreground text-sm">
            管理项目级全局竞品实体，确保名称统一、跨功能项复用
          </p>
        </div>
        <Button
          onClick={openCreate}
          disabled={!canAdmin}
          title={!canAdmin ? "查看者无编辑权限" : undefined}
        >
          <Plus className="mr-2 h-4 w-4" />
          添加竞品
        </Button>
      </div>

      {competitors.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-md border border-dashed py-12 text-center">
          <Building className="text-muted-foreground/40 mb-3 h-12 w-12" />
          <p className="text-muted-foreground text-sm">暂无竞品，点击添加</p>
        </div>
      ) : (
        <div className="space-y-3">
          {competitors.map((c) => (
            <div
              key={c.id}
              className="border-border group flex items-center gap-4 rounded-md border p-4"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{c.name}</span>
                  {c.website && (
                    <a
                      href={c.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-muted-foreground hover:text-foreground"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  )}
                </div>
                {c.description && (
                  <p className="text-muted-foreground mt-0.5 text-sm">{c.description}</p>
                )}
              </div>
              <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={() => openEdit(c)}
                  disabled={!canAdmin}
                >
                  <Pencil className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive h-7 w-7 p-0"
                  onClick={() => {
                    if (confirm("确认删除？关联的竞品参考也会被删除。")) {
                      onDeleteCompetitor(c.id);
                    }
                  }}
                  disabled={!canAdmin}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Dialog */}
      <Dialog open={addDialog} onOpenChange={setAddDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加竞品</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>名称</Label>
              <Input
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="竞品名称"
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label>网站（可选）</Label>
              <Input
                value={formWebsite}
                onChange={(e) => setFormWebsite(e.target.value)}
                placeholder="https://..."
              />
            </div>
            <div className="space-y-2">
              <Label>描述（可选）</Label>
              <Textarea
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                placeholder="简要描述"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddDialog(false)}>
              取消
            </Button>
            <Button onClick={handleCreate} disabled={!formName.trim()}>
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editDialog} onOpenChange={setEditDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑竞品</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>名称</Label>
              <Input value={formName} onChange={(e) => setFormName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>网站（可选）</Label>
              <Input
                value={formWebsite}
                onChange={(e) => setFormWebsite(e.target.value)}
                placeholder="https://..."
              />
            </div>
            <div className="space-y-2">
              <Label>描述（可选）</Label>
              <Textarea
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialog(false)}>
              取消
            </Button>
            <Button onClick={handleUpdate} disabled={!formName.trim()}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
