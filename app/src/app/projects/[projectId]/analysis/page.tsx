"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useState, useRef, useCallback } from "react";
import {
  Bell,
  ChevronRight,
  LogOut,
  Settings,
  Shield,
  AlertTriangle,
  Type,
  FileText,
  ImagePlus,
  X,
  Loader2,
  ChevronDown,
  Save,
  TestTube,
  Scan,
  Globe,
  Sparkles,
} from "lucide-react";
import { GlobalSearchBar } from "@/components/global-search-bar";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { usePageContext } from "@/lib/use-page-context";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { AnalysisResult } from "@/components/analysis-result";
import {
  type AnalysisLevel,
  type LayerResult,
  type StreamChunk,
  type StreamAnalyzeRequest,
  type GenerateTestPointsResponse,
  type AITestPoint,
} from "@/services/analyzer";
import {
  saveAnalysisAction,
  generateTestPointsAIAction,
  saveTestPointsAction,
} from "@/actions/analyze";
import { logActivityAuto } from "@/actions/activity-log";

/** SSE streaming via internal proxy route instead of direct FastAPI call */
function analyzeRequirementStream(
  req: StreamAnalyzeRequest,
  onChunk: (chunk: StreamChunk) => void,
  onError: (error: string) => void,
  onDone: () => void,
): AbortController {
  const controller = new AbortController();
  (async () => {
    try {
      const resp = await fetch("/api/analyze/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
        signal: controller.signal,
      });
      if (!resp.ok) {
        const text = await resp.text();
        onError(`HTTP ${resp.status}: ${text}`);
        return;
      }
      const reader = resp.body?.getReader();
      if (!reader) {
        onError("无法读取响应流");
        return;
      }
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data: ")) continue;
          const jsonStr = trimmed.slice(6);
          if (jsonStr === "[DONE]") {
            onDone();
            return;
          }
          try {
            const chunk = JSON.parse(jsonStr) as StreamChunk;
            onChunk(chunk);
            if (chunk.type === "done") {
              onDone();
              return;
            }
          } catch {
            /* skip malformed */
          }
        }
      }
      onDone();
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        onError(`分析服务不可用: ${(e as Error).message}`);
      }
    }
  })();
  return controller;
}

// File upload types
interface UploadedFile {
  id: string;
  file: File;
  name: string;
  size: string;
  type: "document" | "image";
  status: "uploading" | "completed";
  previewUrl?: string;
}

// AI providers
const AI_PROVIDERS = [
  { value: "default", label: "默认" },
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "deepseek", label: "DeepSeek" },
];

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function createEmptyLayer(level: AnalysisLevel): LayerResult {
  return {
    level,
    affected_modules: [],
    completeness_issues: [],
    suggestions: [],
    isStreaming: true,
    isComplete: false,
  };
}

export default function AnalysisPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const projectId = params.projectId as string;
  const initialNodeId = searchParams.get("nodeId") || "";

  const { projectName, userName, userInitials } = usePageContext(projectId);
  const [requirementText, setRequirementText] = useState("");
  const [nodeId, setNodeId] = useState(initialNodeId);
  const [provider, setProvider] = useState("default");
  const [layers, setLayers] = useState<LayerResult[]>([]);
  const [currentLevel, setCurrentLevel] = useState<AnalysisLevel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [uploadedImages, setUploadedImages] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [testPointsResult, setTestPointsResult] = useState<GenerateTestPointsResponse | null>(null);
  const [isGeneratingPoints, setIsGeneratingPoints] = useState(false);
  const [checkedTestPoints, setCheckedTestPoints] = useState<Set<string>>(new Set());
  const [isSaving, setIsSaving] = useState(false);
  const [isSavingTestPoints, setIsSavingTestPoints] = useState(false);

  // F15: Analysis result flow prompt
  const [analysisFlowMessage, setAnalysisFlowMessage] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const documentInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  const MAX_DOCUMENTS = 3;
  const MAX_IMAGES = 5;

  const hasContent =
    requirementText.trim() || uploadedFiles.length > 0 || uploadedImages.length > 0;
  const hasResults = layers.length > 0;
  const isStreaming = layers.some((l) => l.isStreaming);
  const allLayersDone = layers.length > 0 && layers.every((l) => l.isComplete);
  const highestLevel = layers.length > 0 ? layers[layers.length - 1].level : null;

  // Handle file upload
  const handleFileUpload = useCallback(
    (files: FileList | null, type: "document" | "image") => {
      if (!files) return;

      const currentCount = type === "document" ? uploadedFiles.length : uploadedImages.length;
      const maxCount = type === "document" ? MAX_DOCUMENTS : MAX_IMAGES;
      const allowedExtensions =
        type === "document" ? [".pdf", ".doc", ".docx", ".txt"] : [".png", ".jpg", ".jpeg"];

      const filesToAdd = Array.from(files).slice(0, maxCount - currentCount);

      filesToAdd.forEach((file) => {
        const extension = "." + file.name.split(".").pop()?.toLowerCase();
        if (!allowedExtensions.includes(extension)) return;

        const newFile: UploadedFile = {
          id: Math.random().toString(36).substr(2, 9),
          file,
          name: file.name,
          size: formatFileSize(file.size),
          type,
          status: "uploading",
          previewUrl: type === "image" ? URL.createObjectURL(file) : undefined,
        };

        if (type === "document") {
          setUploadedFiles((prev) => [...prev, newFile]);
        } else {
          setUploadedImages((prev) => [...prev, newFile]);
        }

        setTimeout(
          () => {
            if (type === "document") {
              setUploadedFiles((prev) =>
                prev.map((f) => (f.id === newFile.id ? { ...f, status: "completed" } : f)),
              );
            } else {
              setUploadedImages((prev) =>
                prev.map((f) => (f.id === newFile.id ? { ...f, status: "completed" } : f)),
              );
            }
          },
          800 + Math.random() * 500,
        );
      });
    },
    [uploadedFiles.length, uploadedImages.length],
  );

  const handleRemoveFile = (id: string, type: "document" | "image") => {
    if (type === "document") {
      setUploadedFiles((prev) => prev.filter((f) => f.id !== id));
    } else {
      const file = uploadedImages.find((f) => f.id === id);
      if (file?.previewUrl) URL.revokeObjectURL(file.previewUrl);
      setUploadedImages((prev) => prev.filter((f) => f.id !== id));
    }
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const files = e.dataTransfer.files;
      if (!files.length) return;
      const firstFile = files[0];
      const extension = "." + firstFile.name.split(".").pop()?.toLowerCase();
      if ([".pdf", ".doc", ".docx", ".txt"].includes(extension)) {
        handleFileUpload(files, "document");
      } else if ([".png", ".jpg", ".jpeg"].includes(extension)) {
        handleFileUpload(files, "image");
      }
    },
    [handleFileUpload],
  );

  // Start analysis at a given level
  const startAnalysis = (level: AnalysisLevel) => {
    if (!hasContent && level === "L1") return;
    if (!nodeId) {
      setError("请先选择要分析的功能节点（通过URL参数 ?nodeId=xxx 或从功能项页面进入）");
      return;
    }
    setError(null);
    setCurrentLevel(level);

    // For L1, reset layers; for L2/L3, append
    if (level === "L1") {
      setLayers([createEmptyLayer("L1")]);
      setTestPointsResult(null);
      setCheckedTestPoints(new Set());
    } else {
      setLayers((prev) => [...prev, createEmptyLayer(level)]);
    }

    const controller = analyzeRequirementStream(
      {
        project_id: projectId,
        requirement_text: requirementText,
        node_id: nodeId,
        analysis_level: level,
      },
      (chunk: StreamChunk) => {
        setLayers((prev) => {
          const updated = [...prev];
          const idx = updated.findIndex((l) => l.level === chunk.level);
          if (idx === -1) return prev;
          const layer = { ...updated[idx] };

          if (chunk.type === "modules" && chunk.data.affected_modules) {
            layer.affected_modules = [...layer.affected_modules, ...chunk.data.affected_modules];
          }
          if (chunk.type === "completeness" && chunk.data.completeness_issues) {
            layer.completeness_issues = [
              ...layer.completeness_issues,
              ...chunk.data.completeness_issues,
            ];
          }
          if (chunk.type === "suggestions" && chunk.data.suggestions) {
            layer.suggestions = [...layer.suggestions, ...chunk.data.suggestions];
          }
          if (chunk.type === "metadata" && chunk.data.metadata) {
            layer.metadata = chunk.data.metadata;
          }
          if (chunk.type === "done") {
            layer.isStreaming = false;
            layer.isComplete = true;
          }
          if (chunk.type === "error") {
            layer.isStreaming = false;
            layer.isComplete = true;
          }

          updated[idx] = layer;
          return updated;
        });
      },
      (errMsg) => {
        setError(errMsg);
        setLayers((prev) =>
          prev.map((l) => (l.level === level ? { ...l, isStreaming: false, isComplete: true } : l)),
        );
        setCurrentLevel(null);
      },
      () => {
        setLayers((prev) =>
          prev.map((l) => (l.level === level ? { ...l, isStreaming: false, isComplete: true } : l)),
        );
        setCurrentLevel(null);
      },
    );

    abortRef.current = controller;
  };

  const handleAnalyze = () => startAnalysis("L1");

  const handleGenerateTestPoints = async () => {
    if (!nodeId) {
      setError("请先选择要分析的功能节点");
      return;
    }
    // Serialize analysis layers as the analysis_result string for the backend
    const analysisResult = JSON.stringify(
      layers.map((l) => ({
        level: l.level,
        affected_modules: l.affected_modules,
        completeness_issues: l.completeness_issues,
        suggestions: l.suggestions,
      })),
    );
    setIsGeneratingPoints(true);
    setError(null);

    const result = await generateTestPointsAIAction({
      project_id: projectId,
      node_id: nodeId,
      analysis_result: analysisResult,
      test_depth: "standard",
    });

    setIsGeneratingPoints(false);
    if (result.ok) {
      setTestPointsResult(result.data);
      // Pre-check all — AITestPoint has no id, use index as key
      setCheckedTestPoints(new Set(result.data.test_points.map((_, i) => String(i))));
    } else {
      setError(result.error);
    }
  };

  const handleSaveAnalysis = async () => {
    if (!nodeId) {
      setError("请先选择要分析的功能节点");
      return;
    }
    setIsSaving(true);
    const result = await saveAnalysisAction(projectId, nodeId, layers);
    setIsSaving(false);
    if (!result.ok) {
      setError(result.error);
    } else {
      // F15: Show flow prompt
      const totalModules = layers.reduce((sum, l) => sum + l.affected_modules.length, 0);
      setAnalysisFlowMessage(
        `分析结果已保存到功能项 ${nodeId} 的需求分析维度，涉及 ${totalModules} 个模块`,
      );
      // F15: Log to activity_logs
      logActivityAuto({
        projectId,
        actionType: "analyze",
        targetType: "node",
        targetId: nodeId,
        summary: `AI需求分析完成，涉及 ${totalModules} 个模块`,
        metadata: { layers: layers.length, totalModules },
      });
    }
  };

  const handleSaveTestPoints = async () => {
    if (!nodeId) {
      setError("请先选择要分析的功能节点");
      return;
    }
    if (!testPointsResult) return;
    setIsSavingTestPoints(true);
    // Backend expects full test point objects — select by index
    const selectedPoints = testPointsResult.test_points.filter((_, i) =>
      checkedTestPoints.has(String(i)),
    );
    const result = await saveTestPointsAction(projectId, nodeId, selectedPoints);
    setIsSavingTestPoints(false);
    if (!result.ok) {
      setError(result.error);
    } else {
      setAnalysisFlowMessage(
        `分析结果已保存到功能项 ${nodeId} 的需求分析维度，生成了 ${selectedPoints.length} 条测试点`,
      );
      // F15: Log to activity_logs
      logActivityAuto({
        projectId,
        actionType: "analyze",
        targetType: "node",
        targetId: nodeId,
        summary: `AI生成 ${selectedPoints.length} 条测试点并录入`,
        metadata: { testPointCount: selectedPoints.length },
      });
    }
  };

  const toggleTestPoint = (id: string) => {
    setCheckedTestPoints((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const priorityColor: Record<string, string> = {
    P0: "bg-red-100 text-red-700 border-red-200",
    P1: "bg-yellow-100 text-yellow-700 border-yellow-200",
    P2: "bg-blue-100 text-blue-700 border-blue-200",
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
              <BreadcrumbPage>需求分析工作台</BreadcrumbPage>
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
          className="border-primary text-primary border-b-2 pt-2 pb-3 text-sm font-medium"
        >
          需求工作台
        </Link>
        <Link
          href={`/projects/${projectId}/comparison`}
          className="text-muted-foreground hover:text-foreground pt-2 pb-3 text-sm"
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

      {/* Main Content - 50/50 Split */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Side - Input Area */}
        <div
          className={`border-border flex w-1/2 flex-col border-r p-6 ${
            isDragOver ? "border-primary/50 bg-primary/5 border-2 border-dashed" : ""
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold">需求描述</h2>
            <div className="flex items-center gap-2">
              {/* AI Provider Switcher */}
              <Select value={provider} onValueChange={(v) => v && setProvider(v)}>
                <SelectTrigger className="h-8 w-[120px] text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {AI_PROVIDERS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <TooltipProvider>
                <div className="bg-muted/50 flex items-center gap-1 rounded-md p-0.5">
                  <Tooltip>
                    <TooltipTrigger className="bg-background hover:bg-accent inline-flex h-7 w-7 items-center justify-center rounded-md p-0 shadow-sm">
                      <Type className="h-4 w-4" />
                    </TooltipTrigger>
                    <TooltipContent>文字输入</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger
                      className="hover:bg-background inline-flex h-7 w-7 items-center justify-center rounded-md p-0 disabled:opacity-50"
                      onClick={() => documentInputRef.current?.click()}
                      disabled={uploadedFiles.length >= MAX_DOCUMENTS}
                    >
                      <FileText className="h-4 w-4" />
                    </TooltipTrigger>
                    <TooltipContent>
                      上传文档 ({uploadedFiles.length}/{MAX_DOCUMENTS})
                    </TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger
                      className="hover:bg-background inline-flex h-7 w-7 items-center justify-center rounded-md p-0 disabled:opacity-50"
                      onClick={() => imageInputRef.current?.click()}
                      disabled={uploadedImages.length >= MAX_IMAGES}
                    >
                      <ImagePlus className="h-4 w-4" />
                    </TooltipTrigger>
                    <TooltipContent>
                      上传图片 ({uploadedImages.length}/{MAX_IMAGES})
                    </TooltipContent>
                  </Tooltip>
                </div>
              </TooltipProvider>
            </div>
          </div>

          {/* Node ID selector */}
          {nodeId && (
            <div className="mb-3 flex items-center gap-2">
              <Badge variant="outline" className="text-xs">
                功能节点: {nodeId}
              </Badge>
              <button
                onClick={() => setNodeId("")}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          )}

          {/* Hidden file inputs */}
          <input
            ref={documentInputRef}
            type="file"
            accept=".pdf,.doc,.docx,.txt"
            multiple
            className="hidden"
            onChange={(e) => handleFileUpload(e.target.files, "document")}
          />
          <input
            ref={imageInputRef}
            type="file"
            accept=".png,.jpg,.jpeg"
            multiple
            className="hidden"
            onChange={(e) => handleFileUpload(e.target.files, "image")}
          />

          <Textarea
            className="min-h-[300px] flex-1 resize-none"
            placeholder={
              "输入需求描述，AI 将分析影响范围和完整性...\n\n支持拖拽上传文档 (.pdf, .doc, .docx, .txt) 或图片 (.png, .jpg, .jpeg)"
            }
            value={requirementText}
            onChange={(e) => setRequirementText(e.target.value)}
          />

          {/* Uploaded files display */}
          {(uploadedFiles.length > 0 || uploadedImages.length > 0) && (
            <div className="mt-3 flex flex-wrap gap-2">
              {uploadedFiles.map((file) => (
                <Badge
                  key={file.id}
                  variant="secondary"
                  className="flex items-center gap-1.5 px-2 py-1 text-xs"
                >
                  {file.status === "uploading" ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <FileText className="h-3 w-3" />
                  )}
                  <span className="max-w-[120px] truncate">{file.name}</span>
                  <span className="text-muted-foreground">({file.size})</span>
                  <button
                    onClick={() => handleRemoveFile(file.id, "document")}
                    className="hover:bg-muted-foreground/20 ml-0.5 rounded-full p-0.5"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
              {uploadedImages.map((file) => (
                <Badge
                  key={file.id}
                  variant="secondary"
                  className="flex items-center gap-1.5 px-2 py-1 text-xs"
                >
                  {file.status === "uploading" ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <ImagePlus className="h-3 w-3" />
                  )}
                  <span className="max-w-[120px] truncate">{file.name}</span>
                  <span className="text-muted-foreground">({file.size})</span>
                  <button
                    onClick={() => handleRemoveFile(file.id, "image")}
                    className="hover:bg-muted-foreground/20 ml-0.5 rounded-full p-0.5"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
          )}

          {/* Drag overlay hint */}
          {isDragOver && (
            <div className="bg-primary/5 pointer-events-none absolute inset-0 flex items-center justify-center">
              <div className="text-primary font-medium">松开以上传文件</div>
            </div>
          )}

          <Button
            className="mt-4 w-fit"
            onClick={handleAnalyze}
            disabled={!hasContent || isStreaming}
          >
            {isStreaming && currentLevel === "L1" ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                分析中...
              </>
            ) : (
              "AI 分析"
            )}
          </Button>
        </div>

        {/* Right Side - Analysis Results */}
        <div className="flex w-1/2 flex-col">
          <ScrollArea className="flex-1">
            <div className="space-y-6 p-6">
              {/* F15: Analysis Result Flow Prompt */}
              {analysisFlowMessage && (
                <div className="border-primary/30 bg-primary/5 flex items-center gap-3 rounded-lg border p-4">
                  <Sparkles className="text-primary h-5 w-5 shrink-0" />
                  <p className="flex-1 text-sm">{analysisFlowMessage}</p>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="shrink-0 text-xs"
                    onClick={() => setAnalysisFlowMessage(null)}
                  >
                    知道了
                  </Button>
                </div>
              )}

              {/* Error State */}
              {error && (
                <Card className="border-destructive/60 p-5 shadow-sm">
                  <div className="mb-2 flex items-center gap-2">
                    <AlertTriangle className="text-destructive h-5 w-5" />
                    <h3 className="text-destructive font-medium">分析失败</h3>
                  </div>
                  <p className="text-muted-foreground text-sm">{error}</p>
                  <Button variant="outline" size="sm" className="mt-3" onClick={handleAnalyze}>
                    重试
                  </Button>
                </Card>
              )}

              {/* Empty State */}
              {!hasResults && !error && (
                <div className="text-muted-foreground flex h-[400px] flex-col items-center justify-center">
                  <p className="text-sm">输入需求后点击「AI 分析」查看结果</p>
                </div>
              )}

              {/* Progressive Layer Results */}
              {layers.map((layer) => (
                <div key={layer.level}>
                  <AnalysisResult layer={layer} />

                  {/* Expand button after each complete layer */}
                  {layer.isComplete && layer.level === "L1" && highestLevel === "L1" && (
                    <div className="mt-4 flex justify-center">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => startAnalysis("L2")}
                        disabled={isStreaming}
                        className="gap-2"
                      >
                        <Scan className="h-4 w-4" />
                        扩展分析范围
                        <ChevronDown className="h-3 w-3" />
                      </Button>
                    </div>
                  )}
                  {layer.isComplete && layer.level === "L2" && highestLevel === "L2" && (
                    <div className="mt-4 flex justify-center">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => startAnalysis("L3")}
                        disabled={isStreaming}
                        className="gap-2"
                      >
                        <Globe className="h-4 w-4" />
                        全局扫描
                        <ChevronDown className="h-3 w-3" />
                      </Button>
                    </div>
                  )}

                  {/* Separator between layers */}
                  {layer.level !== highestLevel && (
                    <div className="border-border/60 my-4 border-t" />
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>

          {/* Bottom Action Bar */}
          {hasResults && allLayersDone && !testPointsResult && (
            <div className="border-border bg-card flex items-center justify-between border-t p-4">
              <Button
                variant="outline"
                onClick={handleSaveAnalysis}
                disabled={isSaving}
                className="gap-2"
              >
                <Save className="h-4 w-4" />
                {isSaving ? "保存中..." : "保存到需求分析维度"}
              </Button>
              <Button
                onClick={handleGenerateTestPoints}
                disabled={isGeneratingPoints}
                className="gap-2"
              >
                <TestTube className="h-4 w-4" />
                {isGeneratingPoints ? "生成中..." : "生成测试点"}
              </Button>
            </div>
          )}

          {/* Test Points Results */}
          {testPointsResult && (
            <div className="border-border border-t">
              <ScrollArea className="max-h-[400px]">
                <div className="space-y-4 p-6">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold">测试点 ({testPointsResult.total})</h3>
                    <div className="flex gap-2 text-xs">
                      {["P0", "P1", "P2"].map((p) => {
                        const count = testPointsResult.test_points.filter(
                          (tp) => tp.priority === p,
                        ).length;
                        return count > 0 ? (
                          <Badge key={p} variant="outline" className={priorityColor[p] || ""}>
                            {p}: {count}
                          </Badge>
                        ) : null;
                      })}
                    </div>
                  </div>

                  {["P0", "P1", "P2"].map((priority) => {
                    const points = testPointsResult.test_points
                      .map((p, i) => ({ ...p, _idx: i }))
                      .filter((p) => p.priority === priority);
                    if (points.length === 0) return null;
                    return (
                      <div key={priority}>
                        <div className="mb-2 flex items-center gap-2">
                          <Badge variant="outline" className={priorityColor[priority] || ""}>
                            {priority}
                          </Badge>
                          <span className="text-muted-foreground text-xs">{points.length} 条</span>
                        </div>
                        <div className="space-y-2">
                          {points.map((point) => (
                            <Card key={point._idx} className="border-border/60 p-3">
                              <div className="flex items-start gap-3">
                                <Checkbox
                                  checked={checkedTestPoints.has(String(point._idx))}
                                  onCheckedChange={() => toggleTestPoint(String(point._idx))}
                                  className="mt-0.5"
                                />
                                <div className="flex-1">
                                  <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground font-mono text-xs">
                                      TP-{String(point._idx + 1).padStart(3, "0")}
                                    </span>
                                    <span className="text-sm font-medium">{point.title}</span>
                                  </div>
                                  <p className="text-muted-foreground mt-1 text-xs">
                                    {point.description}
                                  </p>
                                </div>
                                <Badge variant="secondary" className="shrink-0 text-xs">
                                  {point.category}
                                </Badge>
                              </div>
                            </Card>
                          ))}
                        </div>
                      </div>
                    );
                  })}

                  {/* Category Summary */}
                  <div className="text-muted-foreground flex gap-3 border-t pt-2 text-xs">
                    {["functional", "boundary", "exception", "performance"].map((cat) => {
                      const count = testPointsResult.test_points.filter(
                        (p) => p.category === cat,
                      ).length;
                      return count > 0 ? (
                        <span key={cat}>
                          {cat}: {count}
                        </span>
                      ) : null;
                    })}
                  </div>
                </div>
              </ScrollArea>

              {/* Test Points Action Bar */}
              <div className="border-border bg-card flex items-center justify-between border-t p-4">
                <span className="text-muted-foreground text-sm">
                  已选 {checkedTestPoints.size} / {testPointsResult.test_points.length} 条
                </span>
                <Button
                  onClick={handleSaveTestPoints}
                  disabled={isSavingTestPoints || checkedTestPoints.size === 0}
                  className="gap-2"
                >
                  {isSavingTestPoints ? "录入中..." : "一键录入测试分析维度"}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
