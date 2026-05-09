"use client";

import { useState, useTransition, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Upload,
  FileText,
  Folder,
  FolderOpen,
  Check,
  ChevronRight,
  ChevronLeft,
  AlertTriangle,
  FileUp,
  Sparkles,
  RotateCcw,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { AIMappingTable, type AIMappingRow, type Confidence } from "@/components/ai-mapping-table";
import { type ParsedFile, type FileTreeNode } from "@/actions/import";
import {
  aiAnalyzeZip,
  aiAdjustMapping,
  aiConfirmImport,
  aiUndoImport,
  type MappingRow,
  type AIConfirmResult as SAConfirmResult,
} from "@/actions/import-ai";

// ─── Types ───────────────────────────────────────────

type FlatFolder = { id: string; name: string; path: string; depth: number };
type DimOption = { id: number; key: string; name: string };

interface AIImportWizardProps {
  projectId: string;
  projectName: string;
  folders: FlatFolder[];
  dimensions: DimOption[];
}

const AI_STEPS = [
  { label: "上传文件", icon: Upload },
  { label: "文件预览", icon: FileText },
  { label: "AI 分析", icon: Sparkles },
  { label: "确认导入", icon: Check },
];

// ─── Dedup Dialog ────────────────────────────────────

interface DedupItem {
  file_name: string;
  existing_node_name: string;
  existing_node_id: string;
}

type DedupAction = "merge" | "skip" | "create";

interface DedupDialogProps {
  item: DedupItem;
  onDecide: (action: DedupAction) => void;
}

function DedupDialog({ item, onDecide }: DedupDialogProps) {
  return (
    <Dialog open>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-yellow-500" />
            发现同名功能项
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 text-sm">
          <p className="text-muted-foreground">
            文件 <span className="text-foreground font-medium">{item.file_name}</span> 与已有功能项{" "}
            <span className="text-foreground font-medium">{item.existing_node_name}</span>{" "}
            同名，请选择处理方式：
          </p>
          <div className="flex flex-col gap-2">
            <button
              className="hover:bg-muted/80 flex items-start gap-3 rounded-lg border p-3 text-left transition-colors"
              onClick={() => onDecide("merge")}
            >
              <div className="border-primary mt-0.5 h-4 w-4 flex-shrink-0 rounded-full border-2" />
              <div>
                <p className="font-medium">合并到已有功能项</p>
                <p className="text-muted-foreground text-xs">
                  将此文件内容追加到已有功能项的对应维度
                </p>
              </div>
            </button>
            <button
              className="hover:bg-muted/80 flex items-start gap-3 rounded-lg border p-3 text-left transition-colors"
              onClick={() => onDecide("skip")}
            >
              <div className="border-border mt-0.5 h-4 w-4 flex-shrink-0 rounded-full border-2" />
              <div>
                <p className="font-medium">跳过</p>
                <p className="text-muted-foreground text-xs">不导入此文件，保留已有数据不变</p>
              </div>
            </button>
            <button
              className="hover:bg-muted/80 flex items-start gap-3 rounded-lg border p-3 text-left transition-colors"
              onClick={() => onDecide("create")}
            >
              <div className="border-border mt-0.5 h-4 w-4 flex-shrink-0 rounded-full border-2" />
              <div>
                <p className="font-medium">创建新功能项</p>
                <p className="text-muted-foreground text-xs">同名但独立创建，两者并存</p>
              </div>
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── File Tree ───────────────────────────────────────

function FileTreeItem({
  node,
  depth,
  selectedFile,
  onSelect,
  parentPath,
}: {
  node: FileTreeNode;
  depth: number;
  selectedFile: string | null;
  onSelect: (path: string) => void;
  parentPath: string;
}) {
  const [expanded, setExpanded] = useState(true);
  const isFolder = node.type === "folder";
  const nodePath = parentPath ? `${parentPath}/${node.name}` : node.name;
  const isSelected = selectedFile === nodePath;

  return (
    <div>
      <button
        className={cn(
          "hover:bg-muted/80 flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-sm transition-colors",
          isSelected && "bg-primary/10 text-primary",
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => {
          if (isFolder) setExpanded(!expanded);
          else onSelect(nodePath);
        }}
      >
        {isFolder ? (
          expanded ? (
            <FolderOpen className="h-3.5 w-3.5 shrink-0 text-yellow-600" />
          ) : (
            <Folder className="h-3.5 w-3.5 shrink-0 text-yellow-600" />
          )
        ) : (
          <FileText className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
        )}
        <span className="truncate">{node.name}</span>
        {!isFolder && node.format && (
          <Badge variant="outline" className="ml-auto shrink-0 text-[10px]">
            {node.format}
          </Badge>
        )}
      </button>
      {isFolder && expanded && node.children && (
        <div>
          {node.children.map((child) => (
            <FileTreeItem
              key={child.name}
              node={child}
              depth={depth + 1}
              selectedFile={selectedFile}
              onSelect={onSelect}
              parentPath={nodePath}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Step Indicator ──────────────────────────────────

function StepIndicator({ currentStep, steps }: { currentStep: number; steps: typeof AI_STEPS }) {
  return (
    <div className="mx-auto flex max-w-2xl items-center justify-center gap-0">
      {steps.map((step, index) => {
        const completed = index < currentStep;
        const active = index === currentStep;
        const StepIcon = step.icon;
        return (
          <div key={step.label} className="flex items-center">
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-medium transition-colors",
                  completed
                    ? "bg-primary border-primary text-primary-foreground"
                    : active
                      ? "border-primary text-primary bg-primary/10"
                      : "border-border text-muted-foreground bg-muted/30",
                )}
              >
                {completed ? <Check className="h-4 w-4" /> : <StepIcon className="h-4 w-4" />}
              </div>
              <span
                className={cn(
                  "text-sm whitespace-nowrap",
                  active
                    ? "text-primary font-medium"
                    : completed
                      ? "text-foreground"
                      : "text-muted-foreground",
                )}
              >
                {step.label}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div
                className={cn("mx-3 h-px w-16", index < currentStep ? "bg-primary" : "bg-border")}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Format helpers ──────────────────────────────────

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatBadgeColor(format: string) {
  switch (format) {
    case "markdown":
      return "bg-blue-100 text-blue-700 border-blue-200";
    case "csv":
      return "bg-green-100 text-green-700 border-green-200";
    default:
      return "bg-gray-100 text-gray-700 border-gray-200";
  }
}

// ─── Confidence conversion (backend int 0-100 → frontend enum) ──

function toConfidence(n: number): Confidence {
  if (n >= 85) return "high";
  if (n >= 60) return "medium";
  return "low";
}

// ─── Main Component ──────────────────────────────────

export function AIImportWizard({
  projectId,
  projectName,
  folders,
  dimensions,
}: AIImportWizardProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Step state
  const [step, setStep] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Upload state
  const [parsedFiles, setParsedFiles] = useState<ParsedFile[]>([]);
  const [fileTree, setFileTree] = useState<FileTreeNode | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState("");
  const [selectedPreviewFile, setSelectedPreviewFile] = useState<string | null>(null);

  // AI analysis state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [mappingRows, setMappingRows] = useState<AIMappingRow[]>([]);

  // Import progress (F15)
  const [importProgress, setImportProgress] = useState<{
    isImporting: boolean;
    currentFile: string;
    processed: number;
    total: number;
    percent: number;
    assignedModule: string;
  } | null>(null);

  // Import summary (F15)
  const [importSummary, setImportSummary] = useState<SAConfirmResult | null>(null);

  // Dedup dialog
  const [dedupItem, setDedupItem] = useState<DedupItem | null>(null);
  const dedupResolveRef = useRef<((action: DedupAction) => void) | null>(null);

  // Undo
  const [importSessionId, setImportSessionId] = useState<string | null>(null);
  const [createdNodeIds, setCreatedNodeIds] = useState<string[]>([]);
  const [isUndoing, setIsUndoing] = useState(false);
  // Session id from analyze (needed for confirm/undo)
  const [analyzeSessionId, setAnalyzeSessionId] = useState<string | null>(null);
  // Store full mapping rows from server for confirm
  const [serverMappingRows, setServerMappingRows] = useState<MappingRow[]>([]);

  // ─── Upload ─────────────────────────────────────

  const handleUpload = useCallback((file: File) => {
    if (!file.name.endsWith(".zip")) {
      setError("请上传 .zip 格式的文件");
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setError("文件大小不能超过 50MB");
      return;
    }

    setError(null);
    setUploadedFileName(file.name);

    startTransition(async () => {
      try {
        const { uploadZip } = await import("@/actions/import");
        const fd = new FormData();
        fd.append("file", file);
        const result = await uploadZip(fd);

        if (!result.success) {
          setError(result.error);
          return;
        }

        setParsedFiles(result.data.files);
        setFileTree(result.data.tree);

        if (result.data.files.length > 0) {
          setSelectedPreviewFile(result.data.files[0].path);
        }

        setStep(1);
      } catch (e) {
        setError(e instanceof Error ? e.message : "上传失败");
      }
    });
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleUpload(file);
    },
    [handleUpload],
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleUpload(file);
    },
    [handleUpload],
  );

  // ─── AI Analyze ─────────────────────────────────

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setError(null);

    try {
      const filePayload = parsedFiles.map((f) => ({
        name: f.name,
        path: f.path,
        content: f.content,
        format: f.format,
      }));

      const result = await aiAnalyzeZip(projectId, filePayload);

      if (!result.success) {
        throw new Error(result.error);
      }

      const data = result.data;
      setAnalyzeSessionId(data.session_id);
      setServerMappingRows(data.mapping_rows);

      const rows: AIMappingRow[] = data.mapping_rows.map((m) => ({
        id: m.id,
        file_name: m.title,
        file_path: m.source_path,
        recommended_module_id: m.recommended_module_id,
        recommended_module_name: m.recommended_module_name,
        recommended_dimension_id: m.recommended_dimension_id,
        recommended_dimension_name: m.recommended_dimension_name,
        confidence: toConfidence(m.confidence),
        reason: m.reason,
        selected: m.selected,
      }));

      setMappingRows(rows);
      setStep(2);
    } catch (e) {
      setError(e instanceof Error ? e.message : "AI 分析失败");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // ─── Adjust mapping ─────────────────────────────

  const handleAdjustMapping = async (rows: AIMappingRow[]) => {
    // Fire-and-forget to persist adjustments; ignore failure silently
    const adjustments = rows
      .filter((r) => r.override_module_id !== undefined || r.override_dimension_id !== undefined)
      .map((r) => ({
        id: r.id,
        recommended_module_id: r.override_module_id ?? r.recommended_module_id,
        recommended_dimension_id: r.override_dimension_id ?? r.recommended_dimension_id,
      }));

    if (adjustments.length > 0 && analyzeSessionId) {
      aiAdjustMapping(projectId, analyzeSessionId, adjustments).catch(() => {
        // Non-blocking; local state is the source of truth
      });
    }

    setMappingRows(rows);
  };

  // ─── Dedup prompt helper ─────────────────────────

  const promptDedup = (item: DedupItem): Promise<DedupAction> => {
    return new Promise((resolve) => {
      setDedupItem(item);
      dedupResolveRef.current = resolve;
    });
  };

  const handleDedupDecide = (action: DedupAction) => {
    setDedupItem(null);
    dedupResolveRef.current?.(action);
    dedupResolveRef.current = null;
  };

  // ─── Confirm Import ──────────────────────────────

  const handleConfirm = async () => {
    const selected = mappingRows.filter((r) => r.selected);
    if (selected.length === 0) {
      setError("请至少选择一个文件");
      return;
    }
    if (!analyzeSessionId) {
      setError("分析会话已过期，请重新分析");
      return;
    }

    setError(null);

    setImportProgress({
      isImporting: true,
      currentFile: selected[0]?.file_name ?? "",
      processed: 0,
      total: selected.length,
      percent: 0,
      assignedModule: "",
    });

    setStep(3);

    try {
      // Build mapping_rows for server action by merging UI overrides into server data
      const confirmRows: MappingRow[] = selected.map((uiRow) => {
        const serverRow = serverMappingRows.find((s) => s.id === uiRow.id);
        return {
          ...(serverRow ?? {
            id: uiRow.id,
            index: 0,
            title: uiRow.file_name,
            source_path: uiRow.file_path,
            content: "",
            extracted_content: "",
            recommended_module_id: uiRow.recommended_module_id,
            recommended_module_name: uiRow.recommended_module_name,
            recommended_dimension_id: uiRow.recommended_dimension_id,
            recommended_dimension_key: "",
            recommended_dimension_name: uiRow.recommended_dimension_name,
            confidence: uiRow.confidence === "high" ? 90 : uiRow.confidence === "medium" ? 60 : 20,
            reason: uiRow.reason,
            product_line_tags: [],
            conflict: false,
            conflict_message: null,
            existing_node_id: null,
          }),
          selected: true,
          action: (serverRow?.action ?? "import") as "import" | "skip" | "merge",
          // Apply UI overrides
          recommended_module_id: uiRow.override_module_id ?? uiRow.recommended_module_id,
          recommended_dimension_id: uiRow.override_dimension_id ?? uiRow.recommended_dimension_id,
        };
      });

      // Simulate per-file progress animation
      for (let i = 0; i < selected.length; i++) {
        const uiRow = selected[i];
        const moduleId = uiRow.override_module_id ?? uiRow.recommended_module_id;
        const folder = folders.find((f) => f.id === moduleId);
        setImportProgress({
          isImporting: true,
          currentFile: uiRow.file_name,
          processed: i,
          total: selected.length,
          percent: Math.round((i / selected.length) * 100),
          assignedModule: folder?.name ?? uiRow.file_name,
        });
        await new Promise((r) => setTimeout(r, 150));
      }

      const result = await aiConfirmImport(projectId, analyzeSessionId, confirmRows);

      if (!result.success) {
        throw new Error(result.error);
      }

      const data = result.data;

      setImportProgress({
        isImporting: false,
        currentFile: "",
        processed: selected.length,
        total: selected.length,
        percent: 100,
        assignedModule: "",
      });

      setImportSummary(data);
      setImportSessionId(data.session_id);
      setCreatedNodeIds(data.created_node_ids);

      // Auto-redirect after showing summary
      setTimeout(() => {
        router.push(`/projects/${projectId}?imported=true&count=${data.imported}`);
      }, 4000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "导入失败");
      setImportProgress(null);
      setStep(2);
    }
  };

  // ─── Undo ────────────────────────────────────────

  const handleUndo = async () => {
    if (!importSessionId || createdNodeIds.length === 0) return;
    setIsUndoing(true);
    setError(null);

    try {
      const result = await aiUndoImport(projectId, importSessionId, createdNodeIds);

      if (!result.success) {
        throw new Error(result.error);
      }

      router.push(`/projects/${projectId}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "撤销失败");
    } finally {
      setIsUndoing(false);
    }
  };

  // ─── Derived ────────────────────────────────────

  const selectedFile = parsedFiles.find((f) => f.path === selectedPreviewFile);
  const selectedCount = mappingRows.filter((r) => r.selected).length;
  const lowCount = mappingRows.filter((r: AIMappingRow) => r.confidence === "low").length;

  // ─── Render ─────────────────────────────────────

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Step Indicator */}
      <div className="px-6 py-4">
        <StepIndicator currentStep={step} steps={AI_STEPS} />
      </div>

      <Separator />

      {/* Error */}
      {error && (
        <div className="border-destructive/50 bg-destructive/10 text-destructive mx-6 mt-4 flex items-center gap-2 rounded-md border p-3 text-sm">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
          <button className="ml-auto" onClick={() => setError(null)}>
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Step Content */}
      <div style={{ position: "relative", flex: 1, minHeight: 0 }}>
        {/* ─── Step 0: Upload ─────────────────────── */}
        {step === 0 && (
          <div
            className="flex items-center justify-center p-6"
            style={{ position: "absolute", inset: 0 }}
          >
            <Card
              className={cn(
                "w-full max-w-lg cursor-pointer border-2 border-dashed p-12 text-center transition-colors",
                dragOver ? "border-primary bg-primary/5" : "border-border hover:border-primary/50",
                isPending && "pointer-events-none opacity-60",
              )}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={handleFileInput}
              />
              <FileUp className="text-muted-foreground/60 mx-auto mb-4 h-12 w-12" />
              {isPending ? (
                <>
                  <p className="text-lg font-medium">正在解析 {uploadedFileName}...</p>
                  <p className="text-muted-foreground mt-2 text-sm">解析文件内容中，请稍候</p>
                </>
              ) : (
                <>
                  <p className="text-lg font-medium">拖拽 ZIP 压缩包到这里，或点击选择</p>
                  <p className="text-muted-foreground mt-2 text-sm">
                    上传 .zip 压缩包（内含 .md / .csv / .txt 文件），最大 50MB
                  </p>
                  <div className="mt-4 flex items-center justify-center gap-2">
                    <Sparkles className="text-primary h-4 w-4" />
                    <span className="text-primary text-sm font-medium">
                      AI 将自动分析归类到对应模块和维度
                    </span>
                  </div>
                </>
              )}
            </Card>
          </div>
        )}

        {/* ─── Step 1: Preview ────────────────────── */}
        {step === 1 && fileTree && (
          <div style={{ position: "absolute", inset: 0, display: "flex", overflow: "hidden" }}>
            {/* Left: File Tree */}
            <div className="flex min-h-0 w-[260px] flex-col overflow-hidden border-r">
              <div className="border-b px-4 py-3">
                <div className="flex items-center gap-2">
                  <Upload className="text-muted-foreground h-4 w-4" />
                  <span className="truncate text-sm font-medium">{uploadedFileName}</span>
                  <Badge variant="secondary" className="ml-auto text-xs">
                    {parsedFiles.length} 个文件
                  </Badge>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto">
                <div className="py-2">
                  {(fileTree.children ?? []).map((child) => (
                    <FileTreeItem
                      key={child.name}
                      node={child}
                      depth={0}
                      selectedFile={selectedPreviewFile}
                      onSelect={setSelectedPreviewFile}
                      parentPath=""
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Right: File Preview */}
            <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
              {selectedFile ? (
                <>
                  <div className="bg-muted/20 flex shrink-0 items-center justify-between border-b px-6 py-3">
                    <div className="flex items-center gap-2">
                      <FileText className="text-muted-foreground h-4 w-4" />
                      <span className="text-sm font-medium">{selectedFile.name}</span>
                      <Badge
                        variant="outline"
                        className={cn("text-xs", formatBadgeColor(selectedFile.format))}
                      >
                        {selectedFile.format}
                      </Badge>
                    </div>
                    <span className="text-muted-foreground text-xs">
                      {formatSize(selectedFile.size)}
                    </span>
                  </div>
                  <div className="flex-1 overflow-y-auto">
                    <pre className="text-muted-foreground p-6 font-mono text-sm whitespace-pre-wrap">
                      {selectedFile.content}
                    </pre>
                  </div>
                </>
              ) : (
                <div className="text-muted-foreground flex flex-1 items-center justify-center">
                  <p>选择左侧文件查看预览</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ─── Step 2: AI Mapping Table ─────────────── */}
        {step === 2 && (
          <div
            className="flex flex-col"
            style={{ position: "absolute", inset: 0, overflow: "hidden" }}
          >
            {mappingRows.length === 0 ? (
              /* Not yet analyzed — show analyze prompt */
              <div className="flex h-full items-center justify-center">
                <Card className="max-w-md p-8 text-center">
                  <Sparkles className="text-primary mx-auto mb-3 h-10 w-10" />
                  <h3 className="mb-2 text-lg font-semibold">准备好了，开始 AI 分析</h3>
                  <p className="text-muted-foreground mb-6 text-sm">
                    AI 将读取 {parsedFiles.length} 个文件的内容， 推荐模块和维度归属，并标注置信度
                  </p>
                  <Button onClick={handleAnalyze} disabled={isAnalyzing} className="gap-2">
                    {isAnalyzing ? (
                      <>
                        <Sparkles className="h-4 w-4 animate-pulse" />
                        AI 分析中...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4" />
                        开始 AI 分析
                      </>
                    )}
                  </Button>
                  {isAnalyzing && (
                    <p className="text-muted-foreground mt-3 text-xs">
                      正在逐文件读取内容，请稍候...
                    </p>
                  )}
                </Card>
              </div>
            ) : (
              /* Show mapping table */
              <>
                {lowCount > 0 && (
                  <div className="mx-4 mt-3 flex items-center gap-2 rounded-md border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-800">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    <span>有 {lowCount} 条低置信度行（标红），建议人工确认后再导入</span>
                  </div>
                )}
                <div className="mt-2 flex-1 overflow-hidden">
                  <AIMappingTable
                    rows={mappingRows}
                    folders={folders}
                    dimensions={dimensions}
                    onChange={handleAdjustMapping}
                  />
                </div>
              </>
            )}
          </div>
        )}

        {/* ─── Step 3: F15 Progress + Summary ─────── */}
        {step === 3 && (
          <div
            className="mx-auto max-w-2xl space-y-6 p-6"
            style={{ position: "absolute", inset: 0, overflowY: "auto" }}
          >
            {/* F15 Progress Panel */}
            {importProgress && (
              <Card className="p-6">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="flex items-center gap-2 text-sm font-medium">
                    <Sparkles className="text-primary h-4 w-4" />
                    AI 导入进度
                    {importProgress.isImporting ? (
                      <Badge className="bg-primary/10 text-primary hover:bg-primary/10 text-xs">
                        进行中
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="border-green-300 text-xs text-green-600">
                        完成
                      </Badge>
                    )}
                  </h3>
                  <span className="text-muted-foreground text-sm">
                    {importProgress.processed}/{importProgress.total} 文件
                  </span>
                </div>
                {/* Progress bar */}
                <div className="mb-3">
                  <div className="bg-muted flex h-2.5 w-full overflow-hidden rounded-full">
                    <div
                      className="bg-primary rounded-full transition-all duration-300"
                      style={{ width: `${importProgress.percent}%` }}
                    />
                  </div>
                  <span className="text-muted-foreground mt-1 block text-right text-xs">
                    {importProgress.percent}%
                  </span>
                </div>
                {/* Current file */}
                {importProgress.isImporting && importProgress.currentFile && (
                  <div className="bg-primary/5 border-l-primary rounded-md border border-l-4 p-3">
                    <p className="text-sm">
                      <span className="text-muted-foreground">正在处理：</span>
                      <span className="font-medium">{importProgress.currentFile}</span>
                    </p>
                    {importProgress.assignedModule && (
                      <p className="mt-1 text-sm">
                        <span className="text-muted-foreground">归入模块：</span>
                        <Badge variant="outline" className="ml-1 text-xs">
                          {importProgress.assignedModule}
                        </Badge>
                      </p>
                    )}
                  </div>
                )}
              </Card>
            )}

            {/* F15 Import Summary */}
            {importSummary && (
              <Card className="border-green-200 bg-green-50/50 p-6">
                <div className="mb-4 flex items-center gap-2">
                  <Check className="h-5 w-5 text-green-600" />
                  <h3 className="text-base font-semibold text-green-900">导入完成</h3>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="rounded-md border border-green-200 bg-white p-3 text-center">
                    <span className="text-foreground text-2xl font-bold">
                      {importSummary.imported}
                    </span>
                    <p className="text-muted-foreground mt-0.5 text-xs">成功导入</p>
                  </div>
                  <div className="rounded-md border border-green-200 bg-white p-3 text-center">
                    <span className="text-foreground text-2xl font-bold">
                      {importSummary.merged}
                    </span>
                    <p className="text-muted-foreground mt-0.5 text-xs">已合并</p>
                  </div>
                  <div className="rounded-md border border-green-200 bg-white p-3 text-center">
                    <span className="text-foreground text-2xl font-bold">
                      {importSummary.skipped}
                    </span>
                    <p className="text-muted-foreground mt-0.5 text-xs">已跳过</p>
                  </div>
                </div>

                {importSummary.errors.length > 0 && (
                  <div className="mt-3 rounded-md border border-yellow-200 bg-yellow-50 p-3">
                    <p className="mb-1 text-xs font-medium text-yellow-800">
                      部分文件导入时遇到问题：
                    </p>
                    <ul className="space-y-0.5">
                      {importSummary.errors.map((e, i) => (
                        <li key={i} className="text-xs text-yellow-700">
                          {e}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* One-click undo */}
                <div className="mt-4 flex items-center justify-between">
                  <p className="text-muted-foreground text-xs">即将跳转到项目概览页...</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleUndo}
                    disabled={isUndoing}
                    className="text-destructive border-destructive/30 hover:bg-destructive/10 gap-1.5"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    {isUndoing ? "撤销中..." : "一键撤销"}
                  </Button>
                </div>
              </Card>
            )}
          </div>
        )}
      </div>

      {/* Bottom Action Bar */}
      {step > 0 && (
        <div className="bg-card border-t px-6 py-4">
          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              onClick={() => {
                if (step === 2 && mappingRows.length > 0) {
                  // Going back from mapping table: reset rows so user can re-analyze
                  setMappingRows([]);
                }
                setStep(step - 1);
              }}
              disabled={isPending || isAnalyzing || step === 3}
            >
              <ChevronLeft className="mr-1 h-4 w-4" />
              上一步
            </Button>

            <div className="flex items-center gap-3">
              {/* Step 1 → Step 2 (trigger analyze) */}
              {step === 1 && (
                <Button onClick={() => setStep(2)} disabled={isPending}>
                  下一步
                  <ChevronRight className="ml-1 h-4 w-4" />
                </Button>
              )}

              {/* Step 2: analyze button (if not yet analyzed) or confirm */}
              {step === 2 && mappingRows.length === 0 && (
                <Button onClick={handleAnalyze} disabled={isAnalyzing} className="gap-2">
                  {isAnalyzing ? (
                    <>
                      <Sparkles className="h-4 w-4 animate-pulse" />
                      AI 分析中...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" />
                      AI 分析
                    </>
                  )}
                </Button>
              )}
              {step === 2 && mappingRows.length > 0 && (
                <Button onClick={handleConfirm} disabled={selectedCount === 0}>
                  <Check className="mr-1 h-4 w-4" />
                  确认导入（{selectedCount} 个文件）
                </Button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Dedup Dialog */}
      {dedupItem && <DedupDialog item={dedupItem} onDecide={handleDedupDecide} />}
    </div>
  );
}
