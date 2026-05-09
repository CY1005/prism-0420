"use client";

import { useState, useMemo } from "react";
import { ArrowUpDown, ChevronDown, ChevronUp, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
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
import { cn } from "@/lib/utils";

// ─── Types ───────────────────────────────────────────

export type Confidence = "high" | "medium" | "low";

export interface AIMappingRow {
  id: string;
  file_name: string;
  file_path: string;
  recommended_module_id: string;
  recommended_module_name: string;
  recommended_dimension_id: number | null;
  recommended_dimension_name: string;
  confidence: Confidence;
  reason: string;
  selected: boolean;
  // User overrides (if adjusted)
  override_module_id?: string;
  override_dimension_id?: number | null;
}

interface FlatFolder {
  id: string;
  name: string;
  path: string;
  depth: number;
}

interface DimOption {
  id: number;
  key: string;
  name: string;
}

interface AIMappingTableProps {
  rows: AIMappingRow[];
  folders: FlatFolder[];
  dimensions: DimOption[];
  onChange: (rows: AIMappingRow[]) => void;
}

// ─── Confidence helpers ─────────────────────────────

function confidenceLabel(c: Confidence) {
  switch (c) {
    case "high":
      return "高";
    case "medium":
      return "中";
    case "low":
      return "低";
  }
}

function confidenceClass(c: Confidence) {
  switch (c) {
    case "high":
      return "bg-green-100 text-green-700 border-green-300";
    case "medium":
      return "bg-yellow-100 text-yellow-700 border-yellow-300";
    case "low":
      return "bg-red-100 text-red-700 border-red-300";
  }
}

function rowHighlightClass(c: Confidence) {
  if (c === "low") return "bg-red-50/60 hover:bg-red-50";
  return "";
}

type SortKey = "file_name" | "confidence" | "recommended_module_name";
type SortDir = "asc" | "desc";

const CONFIDENCE_ORDER: Record<Confidence, number> = {
  high: 0,
  medium: 1,
  low: 2,
};

// ─── Main Component ──────────────────────────────────

export function AIMappingTable({ rows, folders, dimensions, onChange }: AIMappingTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("confidence");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [filterConfidence, setFilterConfidence] = useState<Confidence | "all">("all");

  // ─── Derived ────────────────────────────────────
  const displayRows = useMemo(() => {
    let filtered = rows;
    if (filterConfidence !== "all") {
      filtered = rows.filter((r) => r.confidence === filterConfidence);
    }

    return [...filtered].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "file_name") {
        cmp = a.file_name.localeCompare(b.file_name);
      } else if (sortKey === "confidence") {
        cmp = CONFIDENCE_ORDER[a.confidence] - CONFIDENCE_ORDER[b.confidence];
      } else if (sortKey === "recommended_module_name") {
        cmp = a.recommended_module_name.localeCompare(b.recommended_module_name);
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [rows, sortKey, sortDir, filterConfidence]);

  const selectedCount = rows.filter((r) => r.selected).length;
  const allSelected = rows.length > 0 && rows.every((r) => r.selected);
  const lowConfidenceCount = rows.filter((r) => r.confidence === "low").length;

  // ─── Sort toggle ────────────────────────────────
  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  // ─── Row mutations (operate on rows by id) ──────
  const updateRow = (id: string, patch: Partial<AIMappingRow>) => {
    onChange(rows.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  };

  const toggleRow = (id: string) => {
    updateRow(id, {
      selected: !rows.find((r) => r.id === id)?.selected,
    });
  };

  const toggleAll = () => {
    onChange(rows.map((r) => ({ ...r, selected: !allSelected })));
  };

  const bulkUpdateModule = (moduleId: string | null) => {
    if (!moduleId) return;
    onChange(rows.map((r) => (r.selected ? { ...r, override_module_id: moduleId } : r)));
  };

  const bulkUpdateDimension = (dimId: string | null) => {
    if (!dimId) return;
    const parsed = dimId !== "none" ? parseInt(dimId) : null;
    onChange(rows.map((r) => (r.selected ? { ...r, override_dimension_id: parsed } : r)));
  };

  // ─── Sort icon ──────────────────────────────────
  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return <ArrowUpDown className="text-muted-foreground/50 ml-1 h-3 w-3" />;
    return sortDir === "asc" ? (
      <ChevronUp className="text-primary ml-1 h-3 w-3" />
    ) : (
      <ChevronDown className="text-primary ml-1 h-3 w-3" />
    );
  };

  // ─── Render ─────────────────────────────────────
  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="bg-muted/20 flex flex-wrap items-center justify-between gap-4 border-b px-4 py-2.5">
        <div className="flex items-center gap-3">
          {/* Toggle all */}
          <Button variant="outline" size="sm" onClick={toggleAll}>
            {allSelected ? "取消全选" : "全选"}
          </Button>

          {/* Bulk module */}
          <Select onValueChange={bulkUpdateModule}>
            <SelectTrigger className="h-7 w-[180px] text-sm">
              <SelectValue placeholder="批量改模块" />
            </SelectTrigger>
            <SelectContent>
              {folders.map((f) => (
                <SelectItem key={f.id} value={f.id}>
                  {f.path}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Bulk dimension */}
          <Select onValueChange={bulkUpdateDimension}>
            <SelectTrigger className="h-7 w-[150px] text-sm">
              <SelectValue placeholder="批量改维度" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">不关联维度</SelectItem>
              {dimensions.map((d) => (
                <SelectItem key={d.id} value={String(d.id)}>
                  {d.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-3">
          {/* Confidence filter */}
          <div className="flex items-center gap-1.5">
            <Filter className="text-muted-foreground h-3.5 w-3.5" />
            <Select
              value={filterConfidence}
              onValueChange={(v) => setFilterConfidence(v as Confidence | "all")}
            >
              <SelectTrigger className="h-7 w-[110px] text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部置信度</SelectItem>
                <SelectItem value="high">仅高</SelectItem>
                <SelectItem value="medium">仅中</SelectItem>
                <SelectItem value="low">仅低</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Badge variant="secondary" className="text-xs">
            已选 {selectedCount}/{rows.length}
          </Badge>
          {lowConfidenceCount > 0 && (
            <Badge variant="outline" className="border-red-300 text-xs text-red-600">
              {lowConfidenceCount} 条需人工确认
            </Badge>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <Table>
          <TableHeader className="bg-muted/80 sticky top-0 z-10">
            <TableRow>
              <TableHead className="w-[40px]">
                <Checkbox checked={allSelected} onCheckedChange={toggleAll} />
              </TableHead>
              <TableHead>
                <button
                  className="flex items-center text-xs font-medium"
                  onClick={() => handleSort("file_name")}
                >
                  文件名
                  <SortIcon col="file_name" />
                </button>
              </TableHead>
              <TableHead>
                <button
                  className="flex items-center text-xs font-medium"
                  onClick={() => handleSort("recommended_module_name")}
                >
                  推荐模块
                  <SortIcon col="recommended_module_name" />
                </button>
              </TableHead>
              <TableHead className="text-xs font-medium">推荐维度</TableHead>
              <TableHead>
                <button
                  className="flex items-center text-xs font-medium"
                  onClick={() => handleSort("confidence")}
                >
                  置信度
                  <SortIcon col="confidence" />
                </button>
              </TableHead>
              <TableHead className="text-xs font-medium">AI 理由</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {displayRows.map((row) => {
              const effectiveModuleId = row.override_module_id ?? row.recommended_module_id;
              const effectiveDimId =
                row.override_dimension_id !== undefined
                  ? row.override_dimension_id
                  : row.recommended_dimension_id;

              return (
                <TableRow
                  key={row.id}
                  className={cn(
                    "transition-colors",
                    !row.selected && "opacity-50",
                    rowHighlightClass(row.confidence),
                  )}
                >
                  <TableCell>
                    <Checkbox checked={row.selected} onCheckedChange={() => toggleRow(row.id)} />
                  </TableCell>

                  {/* File name */}
                  <TableCell>
                    <div className="flex flex-col gap-0.5">
                      <span className="max-w-[180px] truncate text-sm font-medium">
                        {row.file_name}
                      </span>
                      <span className="text-muted-foreground max-w-[180px] truncate text-xs">
                        {row.file_path}
                      </span>
                    </div>
                  </TableCell>

                  {/* Module selector */}
                  <TableCell>
                    <Select
                      value={effectiveModuleId}
                      onValueChange={(v) => v && updateRow(row.id, { override_module_id: v })}
                    >
                      <SelectTrigger className="h-8 w-[180px] text-sm">
                        <SelectValue placeholder="选择模块" />
                      </SelectTrigger>
                      <SelectContent>
                        {folders.map((f) => (
                          <SelectItem key={f.id} value={f.id}>
                            {f.path}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>

                  {/* Dimension selector */}
                  <TableCell>
                    <Select
                      value={effectiveDimId != null ? String(effectiveDimId) : "none"}
                      onValueChange={(v) =>
                        updateRow(row.id, {
                          override_dimension_id: !v || v === "none" ? null : parseInt(v),
                        })
                      }
                    >
                      <SelectTrigger className="h-8 w-[130px] text-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">不关联</SelectItem>
                        {dimensions.map((d) => (
                          <SelectItem key={d.id} value={String(d.id)}>
                            {d.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>

                  {/* Confidence badge */}
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={cn("text-xs", confidenceClass(row.confidence))}
                    >
                      {confidenceLabel(row.confidence)}
                    </Badge>
                  </TableCell>

                  {/* Reason */}
                  <TableCell>
                    <span
                      className="text-muted-foreground block max-w-[220px] truncate text-xs"
                      title={row.reason}
                    >
                      {row.reason}
                    </span>
                  </TableCell>
                </TableRow>
              );
            })}

            {displayRows.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-muted-foreground py-8 text-center text-sm">
                  {filterConfidence !== "all"
                    ? `没有「${confidenceLabel(filterConfidence as Confidence)}」置信度的条目`
                    : "暂无数据"}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
