"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Bell,
  ChevronRight,
  LogOut,
  Settings,
  Shield,
  X,
  Sparkles,
  Loader2,
  Pencil,
  Plus,
  Info,
  Download,
  RefreshCw,
  Trash2,
  Check,
} from "lucide-react";
import { GlobalSearchBar } from "@/components/global-search-bar";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { usePageContext } from "@/lib/use-page-context";
import { getCompetitiveRecords } from "@/actions/nodes";
import { cn } from "@/lib/utils";
import {
  type ComparisonCell,
  type ComparisonRow,
  type ComparisonColumn,
  type ComparisonConclusion,
  type AnalysisMetadata,
} from "@/services/analyzer";
import {
  generateComparisonAction,
  backfillRowAction,
  exportComparisonAction,
} from "@/actions/analyze";

type CompetitiveRecord = {
  nodeId: string;
  nodeName: string;
  nodePath: string;
  recordId: string;
  content: Record<string, unknown>;
};

// ─── Local state row type with editable cells ──────

interface EditableRow {
  dimension: string;
  cells: Record<string, ComparisonCell>;
}

const DEFAULT_DIMENSIONS = ["功能覆盖度", "技术方案差异", "用户体验差异"];
const DEFAULT_FEATURES = ["创建推理服务", "自动扩缩容", "拼卡管理"];

function getCellHighlightClass(score: number | null) {
  if (score !== null && score >= 8) return "bg-green-50";
  if (score !== null && score <= 4) return "bg-red-50";
  return "";
}

export default function ComparisonPage() {
  const params = useParams();
  const projectId = params.projectId as string;

  const { projectName, userName, userInitials } = usePageContext(projectId);

  // Data loading
  const [competitiveRecords, setCompetitiveRecords] = useState<CompetitiveRecord[]>([]);
  const [loadingRecords, setLoadingRecords] = useState(true);

  // Control panel state
  const [selectedFeature, setSelectedFeature] = useState(DEFAULT_FEATURES[0]);
  const [competitors, setCompetitors] = useState<string[]>(["AWS SageMaker", "阿里 PAI"]);
  const [newCompetitor, setNewCompetitor] = useState("");
  const [showAddCompetitor, setShowAddCompetitor] = useState(false);
  const [dimensions, setDimensions] = useState<string[]>([...DEFAULT_DIMENSIONS]);
  const [newDimension, setNewDimension] = useState("");
  const [showAddDimension, setShowAddDimension] = useState(false);

  // Comparison table state
  const [comparisonId, setComparisonId] = useState<string | null>(null);
  const [columns, setColumns] = useState<ComparisonColumn[]>([]);
  const [rows, setRows] = useState<EditableRow[]>([]);
  const [conclusions, setConclusions] = useState<ComparisonConclusion[]>([]);
  const [metadata, setMetadata] = useState<AnalysisMetadata | null>(null);
  const [aiGenerated, setAiGenerated] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);

  // Editing state
  const [editingCell, setEditingCell] = useState<{ row: number; col: string } | null>(null);
  const [editValue, setEditValue] = useState("");
  const [backfillingRow, setBackfillingRow] = useState<number | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCompetitiveRecords(projectId)
      .then((records) => setCompetitiveRecords(records as CompetitiveRecord[]))
      .catch(() => {})
      .finally(() => setLoadingRecords(false));
  }, [projectId]);

  // Add competitor
  const handleAddCompetitor = () => {
    const trimmed = newCompetitor.trim();
    if (trimmed && !competitors.includes(trimmed)) {
      setCompetitors((prev) => [...prev, trimmed]);
      // Add empty cells for new competitor in existing rows
      setRows((prev) =>
        prev.map((row) => ({
          ...row,
          cells: {
            ...row.cells,
            [trimmed]: { value: "", score: null },
          },
        })),
      );
    }
    setNewCompetitor("");
    setShowAddCompetitor(false);
  };

  const handleRemoveCompetitor = (name: string) => {
    setCompetitors((prev) => prev.filter((c) => c !== name));
    setRows((prev) =>
      prev.map((row) => {
        const cells = { ...row.cells };
        delete cells[name];
        return { ...row, cells };
      }),
    );
  };

  // Add dimension
  const handleAddDimension = () => {
    const trimmed = newDimension.trim();
    if (trimmed && !dimensions.includes(trimmed)) {
      setDimensions((prev) => [...prev, trimmed]);
      // Add empty row for new dimension
      const cells: Record<string, ComparisonCell> = {
        ourProduct: { value: "", score: null },
      };
      competitors.forEach((c) => {
        cells[c] = { value: "", score: null };
      });
      setRows((prev) => [...prev, { dimension: trimmed, cells }]);
    }
    setNewDimension("");
    setShowAddDimension(false);
  };

  const handleRemoveDimension = (dim: string) => {
    setDimensions((prev) => prev.filter((d) => d !== dim));
    setRows((prev) => prev.filter((r) => r.dimension !== dim));
  };

  // AI Generate
  const handleGenerate = async () => {
    setAiLoading(true);
    setError(null);

    // Note: In a full implementation, node_ids and competitor_ids would come from
    // real DB entities. For now we pass projectId as the node and empty competitor_ids
    // to let the backend use mock data. The UI still shows feature_name/competitor names.
    const result = await generateComparisonAction({
      project_id: projectId,
      node_ids: [projectId], // placeholder — real impl would use actual node UUIDs
      competitor_ids: [], // placeholder — real impl would use actual competitor UUIDs
      custom_dimensions: dimensions,
    });

    setAiLoading(false);

    if (result.ok) {
      setComparisonId(result.data.comparison_id);
      setColumns(result.data.data.columns);
      // Convert API rows to editable rows
      const editableRows: EditableRow[] = result.data.data.rows.map((r) => ({
        dimension: r.dimension,
        cells: r.cells,
      }));
      setRows(editableRows);
      setConclusions([]); // conclusions are generated separately or can be added later
      setAiGenerated(true);
    } else {
      setError(result.error);
    }
  };

  // Cell editing
  const startEdit = (rowIdx: number, col: string) => {
    setEditingCell({ row: rowIdx, col });
    setEditValue(rows[rowIdx].cells[col]?.value || "");
  };

  const saveEdit = () => {
    if (!editingCell) return;
    setRows((prev) => {
      const updated = [...prev];
      const row = { ...updated[editingCell.row] };
      row.cells = {
        ...row.cells,
        [editingCell.col]: {
          ...row.cells[editingCell.col],
          value: editValue,
        },
      };
      updated[editingCell.row] = row;
      return updated;
    });
    setEditingCell(null);
  };

  const cancelEdit = () => {
    setEditingCell(null);
  };

  // Row operations
  const handleAddRow = () => {
    const cells: Record<string, ComparisonCell> = {
      ourProduct: { value: "", score: null },
    };
    competitors.forEach((c) => {
      cells[c] = { value: "", score: null };
    });
    setRows((prev) => [...prev, { dimension: `维度 ${prev.length + 1}`, cells }]);
  };

  const handleDeleteRow = (idx: number) => {
    setRows((prev) => prev.filter((_, i) => i !== idx));
  };

  // Backfill — write comparison row back to CompetitorReference
  const handleBackfill = async (rowIdx: number) => {
    if (!comparisonId || columns.length === 0) return;
    setBackfillingRow(rowIdx);
    setError(null);

    // Find the first "self" column as node_id and first "competitor" column as competitor_id
    const selfCol = columns.find((c) => c.type === "self");
    const compCol = columns.find((c) => c.type === "competitor");

    if (!selfCol || !compCol) {
      setError("无法找到对应的产品和竞品列");
      setBackfillingRow(null);
      return;
    }

    const result = await backfillRowAction({
      comparison_id: comparisonId,
      row_index: rowIdx,
      node_id: selfCol.id,
      competitor_id: compCol.id,
    });

    setBackfillingRow(null);

    if (!result.ok) {
      setError(result.error);
    }
    // Success: backfill writes to DB, no local row update needed
  };

  // Export
  const handleExport = async () => {
    if (!comparisonId) return;
    setIsExporting(true);
    const result = await exportComparisonAction(comparisonId);
    setIsExporting(false);

    if (result.ok) {
      const blob = new Blob([result.data], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `comparison-${selectedFeature}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } else {
      setError(result.error);
    }
  };

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

      {/* Tab Navigation */}
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
          {/* Control Card */}
          <Card className="border-border/60 mb-6 p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">竞品对比</h2>
              <div className="flex items-center gap-2">
                {aiGenerated && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleExport}
                    disabled={isExporting}
                    className="gap-2"
                  >
                    <Download className="h-4 w-4" />
                    {isExporting ? "导出中..." : "导出"}
                  </Button>
                )}
                <Button
                  onClick={handleGenerate}
                  disabled={aiLoading || competitors.length === 0}
                  className="gap-2"
                >
                  {aiLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      AI 生成中...
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

            <div className="mt-4 flex items-end gap-4">
              <div>
                <Label className="mb-1 block text-sm">选择功能</Label>
                <Select value={selectedFeature} onValueChange={(v) => v && setSelectedFeature(v)}>
                  <SelectTrigger className="w-[220px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DEFAULT_FEATURES.map((f) => (
                      <SelectItem key={f} value={f}>
                        {f}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="mb-1 block text-sm">对比竞品</Label>
                <div className="flex flex-wrap gap-1">
                  {competitors.map((competitor) => (
                    <Badge key={competitor} variant="secondary" className="gap-1">
                      {competitor}
                      <button
                        className="hover:text-foreground"
                        onClick={() => handleRemoveCompetitor(competitor)}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              </div>
              {showAddCompetitor ? (
                <div className="flex items-center gap-1">
                  <Input
                    className="h-8 w-[140px] text-sm"
                    placeholder="竞品名称"
                    value={newCompetitor}
                    onChange={(e) => setNewCompetitor(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAddCompetitor()}
                    autoFocus
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 w-8 p-0"
                    onClick={handleAddCompetitor}
                  >
                    <Check className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 w-8 p-0"
                    onClick={() => setShowAddCompetitor(false)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <Button variant="outline" size="sm" onClick={() => setShowAddCompetitor(true)}>
                  + 添加竞品
                </Button>
              )}
            </div>

            {/* Dimension configuration */}
            <div className="border-border/60 mt-4 border-t pt-4">
              <Label className="mb-2 block text-sm">对比维度</Label>
              <div className="flex flex-wrap items-center gap-2">
                {dimensions.map((dim) => (
                  <Badge key={dim} variant="secondary" className="gap-1">
                    {dim}
                    <button
                      className="hover:text-foreground"
                      onClick={() => handleRemoveDimension(dim)}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
                {showAddDimension ? (
                  <div className="flex items-center gap-1">
                    <Input
                      className="h-7 w-[140px] text-xs"
                      placeholder="维度名称"
                      value={newDimension}
                      onChange={(e) => setNewDimension(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleAddDimension()}
                      autoFocus
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0"
                      onClick={handleAddDimension}
                    >
                      <Check className="h-3 w-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0"
                      onClick={() => setShowAddDimension(false)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 gap-1 text-xs"
                    onClick={() => setShowAddDimension(true)}
                  >
                    <Plus className="h-3 w-3" />
                    添加维度
                  </Button>
                )}
              </div>
            </div>
          </Card>

          {/* Error */}
          {error && (
            <Card className="border-destructive/60 mb-4 p-4 shadow-sm">
              <p className="text-destructive text-sm">{error}</p>
            </Card>
          )}

          {/* AI Generation Banner */}
          {aiGenerated && (
            <div className="mb-4 flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
              <Info className="h-4 w-4 shrink-0 text-blue-500" />
              <div className="flex flex-col gap-1">
                <span className="text-sm text-blue-700">
                  AI已基于已有知识和联网搜索生成对比结果，请review后确认
                </span>
                {metadata && (
                  <span className="text-xs text-blue-600">
                    模型: {metadata.model} | 耗时: {metadata.analysis_time_ms}ms
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Loading State */}
          {aiLoading && (
            <Card className="border-border/60 mb-6 p-12 shadow-sm">
              <div className="flex flex-col items-center justify-center gap-3">
                <Loader2 className="text-primary h-8 w-8 animate-spin" />
                <p className="text-muted-foreground text-sm">
                  AI 正在分析竞品信息并生成对比结果...
                </p>
              </div>
            </Card>
          )}

          {/* Comparison Table */}
          {!aiLoading && rows.length > 0 && (
            <Card className="border-border/60 mb-6 overflow-hidden shadow-sm">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead className="w-28 font-medium">对比维度</TableHead>
                    {columns.map((col) => (
                      <TableHead key={col.id} className="font-medium">
                        {col.name} {col.type === "self" && "(本产品)"}
                      </TableHead>
                    ))}
                    {/* Fallback columns if no AI columns yet */}
                    {columns.length === 0 && (
                      <>
                        <TableHead className="font-medium">本产品</TableHead>
                        {competitors.map((c) => (
                          <TableHead key={c} className="font-medium">
                            {c}
                          </TableHead>
                        ))}
                      </>
                    )}
                    <TableHead className="w-24 font-medium">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row, rowIdx) => {
                    // Determine cell keys: use column IDs if available, else legacy names
                    const cellKeys =
                      columns.length > 0
                        ? columns.map((col) => col.id)
                        : ["ourProduct", ...competitors];

                    return (
                      <TableRow key={rowIdx}>
                        <TableCell className="font-medium">{row.dimension}</TableCell>

                        {/* Dynamic cells based on columns */}
                        {cellKeys.map((colKey) => (
                          <TableCell
                            key={colKey}
                            className={cn(
                              getCellHighlightClass(row.cells[colKey]?.score ?? null),
                              "group relative cursor-pointer",
                            )}
                            onClick={() => startEdit(rowIdx, colKey)}
                          >
                            {editingCell?.row === rowIdx && editingCell?.col === colKey ? (
                              <Input
                                className="h-7 text-sm"
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                onBlur={saveEdit}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") saveEdit();
                                  if (e.key === "Escape") cancelEdit();
                                }}
                                autoFocus
                              />
                            ) : (
                              <>
                                {row.cells[colKey]?.value || (
                                  <span className="text-muted-foreground text-xs">点击编辑</span>
                                )}
                                {row.cells[colKey]?.score != null && (
                                  <span className="text-muted-foreground ml-1 text-xs">
                                    ({row.cells[colKey].score})
                                  </span>
                                )}
                                <button className="hover:bg-muted absolute top-1 right-1 rounded p-1 opacity-0 transition-opacity group-hover:opacity-100">
                                  <Pencil className="text-muted-foreground h-3 w-3" />
                                </button>
                              </>
                            )}
                          </TableCell>
                        ))}

                        {/* Row operations */}
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => handleBackfill(rowIdx)}
                              disabled={backfillingRow === rowIdx || !comparisonId}
                              title="回填到竞品参考"
                            >
                              {backfillingRow === rowIdx ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <RefreshCw className="text-muted-foreground h-3.5 w-3.5" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => handleDeleteRow(rowIdx)}
                              title="删除行"
                            >
                              <Trash2 className="text-muted-foreground h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
              <div className="border-border/60 flex justify-center border-t p-2">
                <Button variant="ghost" size="sm" className="gap-1 text-xs" onClick={handleAddRow}>
                  <Plus className="h-3 w-3" />
                  添加行
                </Button>
              </div>
            </Card>
          )}

          {/* Empty table state (no AI generation yet) */}
          {!aiLoading && rows.length === 0 && !aiGenerated && (
            <Card className="border-border/60 mb-6 p-12 shadow-sm">
              <div className="text-muted-foreground flex flex-col items-center justify-center gap-3">
                <Sparkles className="h-8 w-8" />
                <p className="text-sm">选择功能和竞品后，点击「生成对比」使用 AI 生成对比矩阵</p>
              </div>
            </Card>
          )}

          {/* Conclusion Card */}
          {!aiLoading && conclusions.length > 0 && (
            <Card className="border-border/60 mb-6 p-5 shadow-sm">
              <h3 className="mb-3 font-medium">对比结论（AI 生成）</h3>
              <div className="space-y-2 text-sm">
                {conclusions.map((conclusion, index) => (
                  <p key={index}>
                    <span
                      className={
                        conclusion.type === "advantage" ? "text-green-500" : "text-yellow-500"
                      }
                    >
                      {conclusion.type === "advantage" ? "\u2705" : "\u26A0\uFE0F"}
                    </span>{" "}
                    {conclusion.type === "advantage" ? "优势：" : "劣势："}
                    {conclusion.text}
                  </p>
                ))}
              </div>
            </Card>
          )}

          {/* Real Competitive Records */}
          {!loadingRecords && competitiveRecords.length > 0 && (
            <Card className="border-border/60 p-5 shadow-sm">
              <h3 className="mb-3 font-medium">竞品知识记录（{competitiveRecords.length} 条）</h3>
              <div className="space-y-3">
                {competitiveRecords.map((record) => (
                  <div key={record.recordId} className="border-border rounded-md border p-3">
                    <div className="mb-1 flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        {record.nodeName}
                      </Badge>
                      {record.nodePath && (
                        <span className="text-muted-foreground text-xs">{record.nodePath}</span>
                      )}
                    </div>
                    <p className="text-foreground text-sm">
                      {typeof record.content === "object"
                        ? JSON.stringify(record.content, null, 2).slice(0, 200)
                        : String(record.content)}
                    </p>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
