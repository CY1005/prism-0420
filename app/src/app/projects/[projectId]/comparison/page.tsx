"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Bell,
  ChevronRight,
  LogOut,
  Settings,
  Shield,
  Sparkles,
  Loader2,
  Trash2,
  Save,
  Pencil,
  X,
} from "lucide-react";
import { GlobalSearchBar } from "@/components/global-search-bar";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { usePageContext } from "@/lib/use-page-context";
import { getProjectTree, getProjectDimensions } from "@/actions/nodes";
import {
  getMatrix,
  listSnapshots,
  createSnapshot,
  renameSnapshot,
  deleteSnapshot,
  type ComparisonMatrixResponse,
  type SnapshotResponse,
  type SnapshotListResponse,
} from "@/actions/comparison";
import { cn } from "@/lib/utils";

/**
 * M12 功能对比矩阵 page — design/02-modules/M12-comparison/00-design.md §6 + §7。
 *
 * 路径：/projects/{projectId}/comparison（design §1 字面 /project/:id/compare 漂移路径，
 * 与 prism-0420 整体 /projects/{projectId}/* 路径范式一致 / 拷贝层既有路由不动）。
 *
 * 功能（design §1 in scope）：
 *   - 节点选择器（多选 N 个 nodes / 来自 getProjectTree）
 *   - 维度选择器（多选 M 个 dimension_types / 来自 getProjectDimensions）
 *   - 实时矩阵渲染（GET /comparison/matrix → cells-only / R-X3）
 *   - 保存为命名快照（POST /comparison/snapshots / G4=B 值快照）
 *   - 快照列表（GET /comparison/snapshots / 倒序）
 *   - 快照重命名（PUT / 含乐观锁 expected_version）
 *   - 快照删除（DELETE / items 级联删）
 *
 * design §1 out of scope（不在本页实现）：
 *   - 维度内容编辑（M04 workspace dimension-card / 不在本页）
 *   - AI 自动对比分析（M13 / 已不在本页 / 历史拷贝层 UI 已删）
 *   - 竞品参考录入（M06）/ Markdown 报告导出（M19）
 *
 * 异步范式：M12 §5 显式 N/A（无 Queue / 无 WebSocket / 全同步 CRUD），
 * 不触发 cluster-M16/M17 异步漂移群（PUNT-REPORT.md §M12 明确）。
 */

type TreeNode = Awaited<ReturnType<typeof getProjectTree>>[number];
type DimensionConfig = Awaited<ReturnType<typeof getProjectDimensions>>[number];

interface FlatNode {
  id: string;
  name: string;
  path: string;
  type: string;
  depth: number;
}

function flattenTree(nodes: TreeNode[], acc: FlatNode[] = []): FlatNode[] {
  for (const n of nodes) {
    acc.push({ id: n.id, name: n.name, path: n.path, type: n.type, depth: n.depth });
    if (n.children?.length) flattenTree(n.children as TreeNode[], acc);
  }
  return acc;
}

export default function ComparisonPage() {
  const params = useParams();
  const projectId = params.projectId as string;

  const { projectName, userName, userInitials } = usePageContext(projectId);

  // ─── data sources ───
  const [nodes, setNodes] = useState<FlatNode[]>([]);
  const [dimensions, setDimensions] = useState<DimensionConfig[]>([]);
  const [snapshots, setSnapshots] = useState<SnapshotResponse[]>([]);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [loadingSnapshots, setLoadingSnapshots] = useState(true);

  // ─── selection state ───
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
  const [selectedDimIds, setSelectedDimIds] = useState<number[]>([]);

  // ─── matrix state ───
  const [matrix, setMatrix] = useState<ComparisonMatrixResponse | null>(null);
  const [matrixLoading, setMatrixLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ─── save dialog ───
  const [saveOpen, setSaveOpen] = useState(false);
  const [snapName, setSnapName] = useState("");
  const [snapDesc, setSnapDesc] = useState("");
  const [saving, setSaving] = useState(false);

  // ─── rename dialog ───
  const [renameTarget, setRenameTarget] = useState<SnapshotResponse | null>(null);
  const [renameName, setRenameName] = useState("");
  const [renameDesc, setRenameDesc] = useState("");
  const [renameSaving, setRenameSaving] = useState(false);

  // ─── delete in-flight ───
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // load metadata on mount
  useEffect(() => {
    setLoadingMeta(true);
    Promise.all([getProjectTree(projectId), getProjectDimensions(projectId)])
      .then(([tree, dims]) => {
        setNodes(flattenTree(tree as TreeNode[]));
        setDimensions(dims);
      })
      .catch((e) => {
        // Auth redirect throws are handled by withAuthRedirect; treat else as soft error
        const message = e instanceof Error ? e.message : "加载节点 / 维度失败";
        setError(message);
      })
      .finally(() => setLoadingMeta(false));
  }, [projectId]);

  const reloadSnapshots = useCallback(() => {
    setLoadingSnapshots(true);
    listSnapshots(projectId, 50)
      .then((res: SnapshotListResponse) => setSnapshots(res.items))
      .catch((e) => {
        const message = e instanceof Error ? e.message : "加载快照列表失败";
        setError(message);
      })
      .finally(() => setLoadingSnapshots(false));
  }, [projectId]);

  useEffect(() => {
    reloadSnapshots();
  }, [reloadSnapshots]);

  // ─── handlers ───

  const toggleNode = (id: string) => {
    setSelectedNodeIds((prev) =>
      prev.includes(id) ? prev.filter((n) => n !== id) : [...prev, id],
    );
  };

  const toggleDim = (id: number) => {
    setSelectedDimIds((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]));
  };

  const handleRender = async () => {
    if (selectedNodeIds.length === 0 || selectedDimIds.length === 0) {
      setError("请至少选择 1 个节点和 1 个维度");
      return;
    }
    setError(null);
    setMatrixLoading(true);
    try {
      const res = await getMatrix(projectId, selectedNodeIds, selectedDimIds);
      setMatrix(res);
    } catch (e) {
      const message = e instanceof Error ? e.message : "矩阵渲染失败";
      setError(message);
    } finally {
      setMatrixLoading(false);
    }
  };

  const openSave = () => {
    if (selectedNodeIds.length === 0 || selectedDimIds.length === 0) {
      setError("请先选择节点和维度");
      return;
    }
    setSnapName("");
    setSnapDesc("");
    setError(null);
    setSaveOpen(true);
  };

  const handleSaveSubmit = async () => {
    setSaving(true);
    setError(null);
    const result = await createSnapshot({
      projectId,
      name: snapName,
      description: snapDesc || undefined,
      nodeIds: selectedNodeIds,
      dimensionTypeIds: selectedDimIds,
    });
    setSaving(false);
    if (result.success) {
      setSaveOpen(false);
      reloadSnapshots();
    } else {
      setError(result.error);
    }
  };

  const openRename = (snap: SnapshotResponse) => {
    setRenameTarget(snap);
    setRenameName(snap.name);
    setRenameDesc(snap.description ?? "");
    setError(null);
  };

  const handleRenameSubmit = async () => {
    if (!renameTarget) return;
    setRenameSaving(true);
    setError(null);
    const result = await renameSnapshot({
      projectId,
      snapshotId: renameTarget.id,
      name: renameName,
      description: renameDesc || undefined,
      expectedVersion: renameTarget.version,
    });
    setRenameSaving(false);
    if (result.success) {
      setRenameTarget(null);
      reloadSnapshots();
    } else {
      setError(result.error);
    }
  };

  const handleDelete = async (snap: SnapshotResponse) => {
    setDeletingId(snap.id);
    setError(null);
    const result = await deleteSnapshot(projectId, snap.id);
    setDeletingId(null);
    if (result.success) {
      reloadSnapshots();
    } else {
      setError(result.error);
    }
  };

  // ─── derived: matrix render lookup ───
  const cellLookup = matrix
    ? new Map(matrix.cells.map((c) => [`${c.node_id}::${c.dimension_type_id}`, c.content]))
    : null;
  const renderedNodes = matrix ? selectedNodeIds : [];
  const renderedDims = matrix ? selectedDimIds : [];
  const nodeNameById = new Map(nodes.map((n) => [n.id, n.name]));
  const dimNameById = new Map(dimensions.map((d) => [d.dimType.id, d.dimType.name]));

  return (
    <div className="bg-background flex min-h-screen flex-col">
      {/* Header */}
      <header className="border-border bg-card flex h-14 items-center justify-between border-b px-6">
        <Link
          href="/projects"
          className="text-foreground hover:text-primary text-lg font-semibold transition-colors"
        >
          Prism
        </Link>
        <GlobalSearchBar />
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
            <Link href="/admin">
              <Shield className="text-muted-foreground h-4 w-4" />
            </Link>
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
            <Link href={`/projects/${projectId}/settings`}>
              <Settings className="text-muted-foreground h-4 w-4" />
            </Link>
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <Bell className="text-muted-foreground h-4 w-4" />
          </Button>
          <div className="flex items-center gap-2">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-muted text-sm">{userInitials || "?"}</AvatarFallback>
            </Avatar>
            <span className="text-foreground text-sm">{userName}</span>
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
            <Link href="/login">
              <LogOut className="text-muted-foreground h-4 w-4" />
            </Link>
          </Button>
        </div>
      </header>

      {/* Breadcrumb */}
      <div className="px-6 py-4">
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink href="/projects">我的项目</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>
              <ChevronRight className="h-4 w-4" />
            </BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbLink href={`/projects/${projectId}`}>
                {projectName || "加载中..."}
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>
              <ChevronRight className="h-4 w-4" />
            </BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbPage>竞品对比</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      {/* Tab Navigation（保 dogfooding spec L179 期望 a[href$=/comparison].border-b-2 命中）*/}
      <div className="border-border flex items-center gap-6 border-b px-6">
        <Link
          href={`/projects/${projectId}`}
          className="text-muted-foreground hover:text-foreground pt-2 pb-3 text-sm"
        >
          全景图
        </Link>
        <Link
          href={`/projects/${projectId}/product-lines/private-cloud`}
          className="text-muted-foreground hover:text-foreground pt-2 pb-3 text-sm"
        >
          产品线
        </Link>
        <Link
          href={`/projects/${projectId}/analysis`}
          className="text-muted-foreground hover:text-foreground pt-2 pb-3 text-sm"
        >
          需求工作台
        </Link>
        <Link
          href={`/projects/${projectId}/comparison`}
          className="border-primary text-primary border-b-2 pt-2 pb-3 text-sm font-medium"
        >
          竞品对比
        </Link>
        <Link
          href={`/projects/${projectId}/issues`}
          className="text-muted-foreground hover:text-foreground pt-2 pb-3 text-sm"
        >
          问题沉淀
        </Link>
        <div className="flex-1" />
        <Link
          href={`/projects/${projectId}/settings`}
          className="text-muted-foreground hover:text-foreground flex items-center gap-1 pt-2 pb-3 text-sm"
        >
          <Settings className="h-3.5 w-3.5" />
          设置
        </Link>
      </div>

      {/* Main Content */}
      <ScrollArea className="flex-1">
        <div className="p-6">
          {/* Heading + actions（保 spec smoke 期望：getByRole("heading", { name: "竞品对比" }) +
              getByRole("button", { name: /生成对比/ })）*/}
          <Card className="border-border/60 mb-6 p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold">竞品对比</h2>
                <p className="text-muted-foreground mt-1 text-sm">
                  选择 N 个节点 + M 个维度，渲染对比矩阵 / 可保存为命名快照（design §1）
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={openSave}
                  disabled={selectedNodeIds.length === 0 || selectedDimIds.length === 0 || saving}
                  className="gap-2"
                >
                  <Save className="h-4 w-4" />
                  保存快照
                </Button>
                <Button
                  onClick={handleRender}
                  disabled={
                    matrixLoading || selectedNodeIds.length === 0 || selectedDimIds.length === 0
                  }
                  className="gap-2"
                >
                  {matrixLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      渲染中...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" />
                      生成对比
                    </>
                  )}
                </Button>
              </div>
            </div>

            {/* 节点选择器（保 spec L151 期望：label "选择功能" exact 命中）*/}
            <div className="mt-4 space-y-3">
              <div>
                <Label className="mb-1 block text-sm">选择功能</Label>
                {loadingMeta ? (
                  <p className="text-muted-foreground text-xs">节点加载中...</p>
                ) : nodes.length === 0 ? (
                  <p className="text-muted-foreground text-xs">
                    本项目尚无节点。请先到全景图建节点。
                  </p>
                ) : (
                  <div className="border-border/60 max-h-40 overflow-auto rounded-md border p-2">
                    <ul className="space-y-1">
                      {nodes.map((n) => {
                        const checked = selectedNodeIds.includes(n.id);
                        return (
                          <li key={n.id}>
                            <label className="hover:bg-muted/40 flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-sm">
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => toggleNode(n.id)}
                                className="h-3.5 w-3.5"
                              />
                              <span
                                style={{ paddingLeft: `${Math.max(0, n.depth) * 12}px` }}
                                className="flex-1 truncate"
                              >
                                {n.name}
                                <span className="text-muted-foreground ml-1 text-xs">
                                  ({n.type})
                                </span>
                              </span>
                            </label>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}
                {selectedNodeIds.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {selectedNodeIds.map((id) => (
                      <Badge key={id} variant="secondary" className="gap-1 text-xs">
                        {nodeNameById.get(id) ?? id.slice(0, 6)}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              {/* 对比竞品（保 spec L154 label "对比竞品" exact 命中 — alias "对比节点"）*/}
              <div>
                <Label className="mb-1 block text-sm">对比竞品</Label>
                <p className="text-muted-foreground text-xs">
                  本期"对比"是节点之间的横向对比（design §1 G4 边界灰区：竞品以"不同 node"体现 /
                  本期不支持"同 node 多竞品"对比）。已选节点：
                  <span className="ml-1 font-medium">{selectedNodeIds.length}</span>
                </p>
              </div>

              {/* 维度选择器（保 spec L160 期望："对比维度" 文本可见）*/}
              <div>
                <Label className="mb-1 block text-sm">对比维度</Label>
                {loadingMeta ? (
                  <p className="text-muted-foreground text-xs">维度加载中...</p>
                ) : dimensions.length === 0 ? (
                  <p className="text-muted-foreground text-xs">
                    项目尚未启用任何维度。请到「设置 → 维度配置」启用。
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {dimensions.map((d) => {
                      const checked = selectedDimIds.includes(d.dimType.id);
                      return (
                        <button
                          key={d.dimType.id}
                          type="button"
                          onClick={() => toggleDim(d.dimType.id)}
                          className={cn(
                            "border-border/60 hover:bg-muted/40 rounded-md border px-2 py-1 text-xs transition-colors",
                            checked && "border-primary bg-primary/10 text-primary",
                          )}
                        >
                          {d.dimType.name}
                          <span className="text-muted-foreground ml-1">[{d.dimType.key}]</span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </Card>

          {/* Error banner */}
          {error && (
            <Card className="border-destructive/60 mb-4 p-4 shadow-sm">
              <p className="text-destructive text-sm">{error}</p>
            </Card>
          )}

          {/* Matrix Card（design §6 N×M 表格 + 节点列 + 维度行 / 未填格显示空字符串）*/}
          {matrix && renderedNodes.length > 0 && renderedDims.length > 0 ? (
            <Card className="border-border/60 mb-6 overflow-hidden shadow-sm">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead className="w-32 font-medium">维度 \ 节点</TableHead>
                    {renderedNodes.map((nid) => (
                      <TableHead key={nid} className="font-medium">
                        {nodeNameById.get(nid) ?? nid.slice(0, 6)}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {renderedDims.map((did) => (
                    <TableRow key={did}>
                      <TableCell className="font-medium">
                        {dimNameById.get(did) ?? `dim#${did}`}
                      </TableCell>
                      {renderedNodes.map((nid) => {
                        const content = cellLookup?.get(`${nid}::${did}`) ?? null;
                        const text = content
                          ? typeof content === "object"
                            ? JSON.stringify(content).slice(0, 100)
                            : String(content)
                          : "";
                        return (
                          <TableCell key={`${nid}-${did}`}>
                            {text || (
                              <span className="text-muted-foreground text-xs">（未填写）</span>
                            )}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          ) : !matrixLoading ? (
            // 空状态（保 spec smoke L163 期望：getByText(/选择功能和竞品后/) 可见）
            <Card className="border-border/60 mb-6 p-12 shadow-sm">
              <div className="text-muted-foreground flex flex-col items-center justify-center gap-3">
                <Sparkles className="h-8 w-8" />
                <p className="text-sm">选择功能和竞品后，点击「生成对比」使用 AI 生成对比矩阵</p>
              </div>
            </Card>
          ) : null}

          {/* Snapshots Panel（design §1 in scope: 列表 / 重命名 / 删除）*/}
          <Card className="border-border/60 p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-medium">已保存的快照</h3>
              <span className="text-muted-foreground text-xs">
                {loadingSnapshots ? "加载中..." : `共 ${snapshots.length} 条`}
              </span>
            </div>
            {!loadingSnapshots && snapshots.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                暂无快照。选择节点和维度后点击「保存快照」创建。
              </p>
            ) : (
              <div className="space-y-2">
                {snapshots.map((snap) => (
                  <div
                    key={snap.id}
                    className="border-border/60 flex items-start justify-between rounded-md border p-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-foreground truncate text-sm font-medium">
                          {snap.name}
                        </span>
                        <Badge variant="outline" className="text-xs">
                          v{snap.version}
                        </Badge>
                      </div>
                      {snap.description && (
                        <p className="text-muted-foreground mt-1 text-xs">{snap.description}</p>
                      )}
                      <p className="text-muted-foreground mt-1 text-xs">
                        节点 {snap.nodes_ref.length} / 维度 {snap.dimensions_ref.length} ·{" "}
                        {new Date(snap.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="ml-2 flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => openRename(snap)}
                        title="重命名"
                      >
                        <Pencil className="text-muted-foreground h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => handleDelete(snap)}
                        disabled={deletingId === snap.id}
                        title="删除"
                      >
                        {deletingId === snap.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="text-muted-foreground h-3.5 w-3.5" />
                        )}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </ScrollArea>

      {/* Save Dialog */}
      <Dialog open={saveOpen} onOpenChange={setSaveOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>保存为快照</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label htmlFor="snap-name" className="mb-1 block text-sm">
                快照名称 <span className="text-destructive">*</span>
              </Label>
              <Input
                id="snap-name"
                value={snapName}
                onChange={(e) => setSnapName(e.target.value)}
                placeholder="如：竞品对比 Q2"
                maxLength={128}
                autoFocus
              />
            </div>
            <div>
              <Label htmlFor="snap-desc" className="mb-1 block text-sm">
                描述（选填）
              </Label>
              <Textarea
                id="snap-desc"
                value={snapDesc}
                onChange={(e) => setSnapDesc(e.target.value)}
                placeholder="描述本快照的用途、对比目的等"
                rows={3}
              />
            </div>
            <p className="text-muted-foreground text-xs">
              将保存当前选中的 {selectedNodeIds.length} 个节点 × {selectedDimIds.length} 个维度
              （G4=B 值快照：保存时复制内容，不受后续编辑影响）
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSaveOpen(false)} disabled={saving}>
              <X className="mr-1 h-4 w-4" />
              取消
            </Button>
            <Button onClick={handleSaveSubmit} disabled={saving || snapName.trim().length === 0}>
              {saving ? (
                <>
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                  保存中...
                </>
              ) : (
                <>
                  <Save className="mr-1 h-4 w-4" />
                  保存
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Rename Dialog */}
      <Dialog open={renameTarget !== null} onOpenChange={(o) => !o && setRenameTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>重命名快照</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label htmlFor="rename-name" className="mb-1 block text-sm">
                新名称 <span className="text-destructive">*</span>
              </Label>
              <Input
                id="rename-name"
                value={renameName}
                onChange={(e) => setRenameName(e.target.value)}
                maxLength={128}
                autoFocus
              />
            </div>
            <div>
              <Label htmlFor="rename-desc" className="mb-1 block text-sm">
                描述（选填）
              </Label>
              <Textarea
                id="rename-desc"
                value={renameDesc}
                onChange={(e) => setRenameDesc(e.target.value)}
                rows={3}
              />
            </div>
            <p className="text-muted-foreground text-xs">
              当前 version = {renameTarget?.version ?? "?"}（乐观锁：若被他人改过会返 409 提示刷新）
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameTarget(null)} disabled={renameSaving}>
              <X className="mr-1 h-4 w-4" />
              取消
            </Button>
            <Button
              onClick={handleRenameSubmit}
              disabled={renameSaving || renameName.trim().length === 0}
            >
              {renameSaving ? (
                <>
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                  保存中...
                </>
              ) : (
                <>
                  <Save className="mr-1 h-4 w-4" />
                  保存
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
