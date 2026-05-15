"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, Sparkles, List, FileText, Upload, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { ImportWizard } from "./import-wizard";
import { AIImportWizard } from "@/components/ai-import-wizard";
import { confirmImport } from "@/actions/import";

type ImportMode = "manual" | "ai" | "markdown";

interface ImportPageClientProps {
  projectId: string;
  projectName: string;
  folders: { id: string; name: string; path: string; depth: number }[];
  dimensions: { id: number; key: string; name: string }[];
  /** M02 项目 AI provider 配置（NULL 时 AI 智能导入 tab 阻断 / 引导先去 settings）。
   *  对应 B-P2-M17-design-gap-fresh-project-blocked: import_router.py L124 字面
   *  `if not ai_provider: raise ImportInvalidSourceError(reason="ai_provider_unset")`。
   *  无前置检查 → 用户上传 zip 后才知道踩坑（422 阻断 UX 不友好）。
   */
  aiProvider: string | null;
}

export function ImportPageClient({
  projectId,
  projectName,
  folders,
  dimensions,
  aiProvider,
}: ImportPageClientProps) {
  const [mode, setMode] = useState<ImportMode>("manual");

  return (
    <div className="bg-background fixed inset-0 flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b px-6">
        <div className="flex items-center gap-3">
          <Link
            href={`/projects/${projectId}`}
            className="text-muted-foreground hover:text-foreground text-sm transition-colors"
          >
            <ChevronLeft className="mr-1 inline h-4 w-4" />
            {projectName}
          </Link>
          <Separator orientation="vertical" className="h-6" />
          <h1 className="text-lg font-semibold">导入文档</h1>
        </div>

        {/* Tab switcher */}
        <div className="bg-muted/30 flex items-center gap-1 rounded-lg border p-1">
          <button
            onClick={() => setMode("manual")}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              mode === "manual"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <List className="h-3.5 w-3.5" />
            手动映射
          </button>
          <button
            onClick={() => setMode("ai")}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              mode === "ai"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Sparkles className="h-3.5 w-3.5" />
            AI 智能导入
          </button>
          <button
            onClick={() => setMode("markdown")}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              mode === "markdown"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <FileText className="h-3.5 w-3.5" />
            Markdown 导入
          </button>
        </div>

        <Link href={`/projects/${projectId}`}>
          <Button variant="outline" size="sm">
            取消
          </Button>
        </Link>
      </header>

      {/* Content */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {mode === "manual" ? (
          <ImportWizard
            projectId={projectId}
            projectName={projectName}
            folders={folders}
            dimensions={dimensions}
            standalone={false}
          />
        ) : mode === "ai" ? (
          aiProvider ? (
            <AIImportWizard
              projectId={projectId}
              projectName={projectName}
              folders={folders}
              dimensions={dimensions}
            />
          ) : (
            <AIProviderUnsetGuide projectId={projectId} />
          )
        ) : (
          <MarkdownImport projectId={projectId} folders={folders} dimensions={dimensions} />
        )}
      </div>
    </div>
  );
}

// ─── AI Provider Unset Guide ─────────────────────────
// B-P2-M17-design-gap-fresh-project-blocked: fresh project ai_provider=NULL 时
// AI 智能导入 tab 必失败（backend 422 IMPORT_INVALID_SOURCE reason=ai_provider_unset）。
// 进入 tab 前显式引导用户先去 settings 配置 AI provider，避免 422 阻断后才反应过来。

function AIProviderUnsetGuide({ projectId }: { projectId: string }) {
  return (
    <div className="flex h-full items-center justify-center p-6">
      <Card className="max-w-md p-8 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-yellow-100">
          <AlertTriangle className="h-6 w-6 text-yellow-600" />
        </div>
        <h3 className="mb-2 text-lg font-semibold">需要先配置 AI Provider</h3>
        <p className="text-muted-foreground mb-6 text-sm">
          AI 智能导入需要项目级 AI Provider 配置（Claude / Codex / Kimi 等）。 请先在项目设置中选择
          Provider 并填入 API Key，再回到这里上传 zip。
        </p>
        <Link href={`/projects/${projectId}/settings`}>
          <Button className="gap-2">
            <Sparkles className="h-4 w-4" />
            去项目设置配置 AI
          </Button>
        </Link>
        <p className="text-muted-foreground mt-4 text-xs">
          已配置请刷新页面；或先用「手动映射」/「Markdown 导入」tab 入库。
        </p>
      </Card>
    </div>
  );
}

// ─── Markdown Single-file Import ────────────────────

function MarkdownImport({
  projectId,
  folders,
  dimensions,
}: {
  projectId: string;
  folders: { id: string; name: string; path: string; depth: number }[];
  dimensions: { id: number; key: string; name: string }[];
}) {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [fileContent, setFileContent] = useState("");
  const [targetFolderId, setTargetFolderId] = useState("");
  const [nodeName, setNodeName] = useState("");
  const [dimensionTypeId, setDimensionTypeId] = useState<string>("");
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!f.name.endsWith(".md") && !f.name.endsWith(".markdown")) {
      setError("请选择 Markdown 文件（.md）");
      return;
    }
    setError("");
    setFile(f);
    setNodeName(f.name.replace(/\.(md|markdown)$/, ""));
    const reader = new FileReader();
    reader.onload = (ev) => {
      setFileContent((ev.target?.result as string) || "");
    };
    reader.readAsText(f);
  };

  const handleImport = async () => {
    if (!file || !targetFolderId || !nodeName.trim()) return;
    setImporting(true);
    setError("");
    try {
      const result = await confirmImport(projectId, [
        {
          fileName: file.name,
          content: fileContent,
          targetNodeId: targetFolderId,
          nodeName: nodeName.trim(),
          dimensionTypeId:
            dimensionTypeId && dimensionTypeId !== "none" ? parseInt(dimensionTypeId) : undefined,
        },
      ]);
      if (result.success) {
        router.push(`/projects/${projectId}`);
      } else {
        setError(result.error);
      }
    } catch {
      setError("导入失败，请重试");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg space-y-6 px-6 py-8">
      <div>
        <h2 className="mb-1 text-lg font-semibold">导入 Markdown 文件</h2>
        <p className="text-muted-foreground text-sm">选择一个 .md 文件，将其内容导入为一个功能项</p>
      </div>

      {/* File selection */}
      <Card className="p-4">
        <div className="space-y-3">
          <Label>选择文件</Label>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
              <Upload className="mr-2 h-4 w-4" />
              选择 .md 文件
            </Button>
            {file && <span className="text-muted-foreground text-sm">{file.name}</span>}
            <input
              ref={fileInputRef}
              type="file"
              accept=".md,.markdown"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>
        </div>
      </Card>

      {file && (
        <>
          {/* Node name */}
          <div className="space-y-2">
            <Label>功能项名称</Label>
            <Input
              value={nodeName}
              onChange={(e) => setNodeName(e.target.value)}
              placeholder="输入功能项名称"
            />
          </div>

          {/* Target folder */}
          <div className="space-y-2">
            <Label>目标模块</Label>
            <Select value={targetFolderId} onValueChange={(v) => v && setTargetFolderId(v)}>
              <SelectTrigger>
                <SelectValue placeholder="选择目标模块..." />
              </SelectTrigger>
              <SelectContent>
                {folders.map((f) => (
                  <SelectItem key={f.id} value={f.id}>
                    {"  ".repeat(f.depth)}
                    {f.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Dimension type */}
          <div className="space-y-2">
            <Label>映射到维度（可选）</Label>
            <Select value={dimensionTypeId} onValueChange={(v) => setDimensionTypeId(v ?? "")}>
              <SelectTrigger>
                <SelectValue placeholder="不映射维度" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">不映射维度</SelectItem>
                {dimensions.map((d) => (
                  <SelectItem key={d.id} value={String(d.id)}>
                    {d.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Preview */}
          {fileContent && (
            <div className="space-y-2">
              <Label>内容预览</Label>
              <div className="bg-muted/30 max-h-40 overflow-auto rounded-md border p-3">
                <pre className="text-muted-foreground text-xs whitespace-pre-wrap">
                  {fileContent.slice(0, 500)}
                  {fileContent.length > 500 ? "..." : ""}
                </pre>
              </div>
            </div>
          )}

          {error && <p className="text-destructive text-sm">{error}</p>}

          <Button
            className="w-full"
            onClick={handleImport}
            disabled={!targetFolderId || !nodeName.trim() || importing}
          >
            {importing ? "导入中..." : "确认导入"}
          </Button>
        </>
      )}
    </div>
  );
}
