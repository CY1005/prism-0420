"use client";

import { useState, useRef, useCallback } from "react";
import { Upload, AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { importNodesFromCSV } from "@/actions/nodes";

interface ParsedRow {
  rowNum: number;
  name: string;
  type: string;
  parent: string;
  desc: string;
  error?: string;
}

interface ImportCSVModalProps {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function parseCSVContent(raw: string): ParsedRow[] {
  const lines = raw.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length < 2) return [];

  const headerRaw = lines[0].replace(/^\uFEFF/, "");
  const headers = headerRaw.split(",").map((h) => h.trim());

  const colIndex = {
    name: headers.indexOf("名称"),
    type: headers.indexOf("类型"),
    parent: headers.indexOf("父节点名称"),
    desc: headers.indexOf("描述"),
  };

  if (colIndex.name === -1) {
    return [{ rowNum: 1, name: "", type: "", parent: "", desc: "", error: "CSV 缺少必填列：名称" }];
  }

  const rows: ParsedRow[] = [];
  const dataLines = lines.slice(1);

  for (let i = 0; i < dataLines.length; i++) {
    const cols = dataLines[i].split(",").map((c) => c.trim());
    const name = colIndex.name >= 0 ? (cols[colIndex.name] ?? "") : "";
    const type = colIndex.type >= 0 ? (cols[colIndex.type] ?? "") : "";
    const parent = colIndex.parent >= 0 ? (cols[colIndex.parent] ?? "") : "";
    const desc = colIndex.desc >= 0 ? (cols[colIndex.desc] ?? "") : "";

    let error: string | undefined;
    if (!name.trim()) {
      error = "名称为空";
    } else if (type && !["folder", "file", "文件夹", "文件", ""].includes(type)) {
      error = `类型 "${type}" 无效（应为 folder/file）`;
    }

    rows.push({ rowNum: i + 2, name, type, parent, desc, error });
  }

  return rows;
}

const TEMPLATE_CONTENT = `名称,类型,父节点名称,描述
产品线A,folder,,核心产品线
模块1,folder,产品线A,功能模块1
功能点1,file,模块1,具体功能描述`;

export function ImportCSVModal({ projectId, open, onOpenChange }: ImportCSVModalProps) {
  const [inputMode, setInputMode] = useState<"file" | "text">("file");
  const [csvText, setCsvText] = useState("");
  const [previewRows, setPreviewRows] = useState<ParsedRow[]>([]);
  const [isParsed, setIsParsed] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [importResult, setImportResult] = useState<{ imported: number; errors: string[] } | null>(
    null,
  );
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      setCsvText(text);
      setPreviewRows(parseCSVContent(text));
      setIsParsed(true);
      setImportResult(null);
    };
    reader.readAsText(file, "utf-8");
  }, []);

  const handleTextParse = useCallback(() => {
    if (!csvText.trim()) return;
    setPreviewRows(parseCSVContent(csvText));
    setIsParsed(true);
    setImportResult(null);
  }, [csvText]);

  const handleImport = useCallback(async () => {
    if (!csvText.trim()) return;
    setIsImporting(true);
    try {
      const result = await importNodesFromCSV(projectId, csvText);
      if (result.success) {
        setImportResult(result.data);
      } else {
        setImportResult({ imported: 0, errors: [result.error] });
      }
    } finally {
      setIsImporting(false);
    }
  }, [projectId, csvText]);

  const handleClose = useCallback(() => {
    if (isImporting) return;
    onOpenChange(false);
    // 延迟重置，等动画结束
    setTimeout(() => {
      setCsvText("");
      setPreviewRows([]);
      setIsParsed(false);
      setImportResult(null);
      setInputMode("file");
      if (fileInputRef.current) fileInputRef.current.value = "";
    }, 300);
  }, [isImporting, onOpenChange]);

  const hasErrors = previewRows.some((r) => !!r.error);
  const validRows = previewRows.filter((r) => !r.error);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>CSV 导入知识节点</DialogTitle>
        </DialogHeader>

        {/* 结果展示 */}
        {importResult ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              成功导入 {importResult.imported} 条节点
            </div>
            {importResult.errors.length > 0 && (
              <div className="space-y-1 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                <p className="flex items-center gap-1 font-medium">
                  <AlertCircle className="h-4 w-4" />
                  {importResult.errors.length} 条跳过
                </p>
                <ul className="list-disc space-y-0.5 pl-5">
                  {importResult.errors.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              </div>
            )}
            <DialogFooter>
              <Button onClick={handleClose}>关闭</Button>
            </DialogFooter>
          </div>
        ) : (
          <div className="space-y-4">
            {/* 模式切换 */}
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setInputMode("file");
                  setIsParsed(false);
                }}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  inputMode === "file"
                    ? "bg-primary text-primary-foreground"
                    : "border-border bg-background hover:bg-muted border"
                }`}
              >
                上传文件
              </button>
              <button
                onClick={() => {
                  setInputMode("text");
                  setIsParsed(false);
                }}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  inputMode === "text"
                    ? "bg-primary text-primary-foreground"
                    : "border-border bg-background hover:bg-muted border"
                }`}
              >
                粘贴文本
              </button>
            </div>

            {/* 格式提示 */}
            <div className="border-border bg-muted/40 text-muted-foreground rounded-lg border px-3 py-2 text-xs">
              <p className="mb-1 font-medium">CSV 列格式：</p>
              <code className="block font-mono whitespace-pre">{TEMPLATE_CONTENT}</code>
            </div>

            {/* 文件上传 */}
            {inputMode === "file" && (
              <div
                className="border-border bg-muted/20 hover:border-primary/50 flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-6 py-8 transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="text-muted-foreground h-8 w-8" />
                <p className="text-muted-foreground text-sm">点击选择 .csv 文件，或拖拽到此处</p>
                {csvText && (
                  <p className="text-xs text-green-600">
                    已读取文件，共 {previewRows.length} 行数据
                  </p>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,text/csv"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </div>
            )}

            {/* 文本粘贴 */}
            {inputMode === "text" && (
              <div className="space-y-2">
                <Textarea
                  placeholder={`粘贴 CSV 内容，例如：\n${TEMPLATE_CONTENT}`}
                  className="min-h-[140px] font-mono text-xs"
                  value={csvText}
                  onChange={(e) => {
                    setCsvText(e.target.value);
                    setIsParsed(false);
                  }}
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleTextParse}
                  disabled={!csvText.trim()}
                >
                  解析预览
                </Button>
              </div>
            )}

            {/* 预览表格 */}
            {isParsed && previewRows.length > 0 && (
              <div className="space-y-2">
                <p className="text-muted-foreground text-sm">
                  预览：{validRows.length} 条有效，{previewRows.length - validRows.length} 条有误
                  {hasErrors && <span className="ml-1 text-amber-600">（红色行将被跳过）</span>}
                </p>
                <div className="border-border max-h-56 overflow-y-auto rounded-lg border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12">行</TableHead>
                        <TableHead>名称</TableHead>
                        <TableHead>类型</TableHead>
                        <TableHead>父节点</TableHead>
                        <TableHead>描述</TableHead>
                        <TableHead>状态</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {previewRows.map((row) => (
                        <TableRow
                          key={row.rowNum}
                          className={row.error ? "bg-red-50 hover:bg-red-50" : ""}
                        >
                          <TableCell className="text-muted-foreground">{row.rowNum}</TableCell>
                          <TableCell className={row.error ? "text-red-700" : ""}>
                            {row.name || "—"}
                          </TableCell>
                          <TableCell>{row.type || "file"}</TableCell>
                          <TableCell>{row.parent || "—"}</TableCell>
                          <TableCell className="max-w-[120px] truncate">
                            {row.desc || "—"}
                          </TableCell>
                          <TableCell>
                            {row.error ? (
                              <span className="flex items-center gap-1 text-xs text-red-600">
                                <AlertCircle className="h-3 w-3" />
                                {row.error}
                              </span>
                            ) : (
                              <span className="flex items-center gap-1 text-xs text-green-600">
                                <CheckCircle2 className="h-3 w-3" />
                                正常
                              </span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}

            {isParsed && previewRows.length === 0 && (
              <p className="text-muted-foreground py-4 text-center text-sm">未解析到任何数据行</p>
            )}

            <DialogFooter>
              <Button variant="outline" onClick={handleClose} disabled={isImporting}>
                取消
              </Button>
              <Button
                onClick={handleImport}
                disabled={!isParsed || validRows.length === 0 || isImporting}
              >
                {isImporting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    导入中...
                  </>
                ) : (
                  `确认导入（${validRows.length} 条）`
                )}
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
