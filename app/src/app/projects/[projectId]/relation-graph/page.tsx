"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { RelationGraph } from "@/components/relation-graph";
import { getRelationGraph, getModuleRelationDetail } from "@/actions/relations";
import { getAffectedNodes } from "@/actions/analyze";

type RelationType = "depends_on" | "related_to" | "conflicts_with";

const relationTypeConfig: Record<RelationType, { label: string; dotClass: string }> = {
  depends_on: { label: "依赖", dotClass: "bg-blue-400" },
  related_to: { label: "相关", dotClass: "bg-gray-400" },
  conflicts_with: { label: "冲突", dotClass: "bg-red-400" },
};

export default function RelationGraphPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const projectId = params.projectId as string;
  const nodeId = searchParams.get("nodeId") ?? null;

  const [graphData, setGraphData] = useState<{
    nodes: { id: string; name: string; featureCount: number; completionPercent: number }[];
    edges: {
      sourceModuleId: string;
      targetModuleId: string;
      relationType: string;
      count: number;
    }[];
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<string, boolean>>({
    depends_on: true,
    related_to: true,
    conflicts_with: true,
  });
  const [affectedNodeIds, setAffectedNodeIds] = useState<string[]>([]);

  useEffect(() => {
    setLoading(true);
    getRelationGraph(projectId).then((result) => {
      setLoading(false);
      if (result.success) {
        setGraphData(result.data);
      } else {
        setError(result.error);
      }
    });
  }, [projectId]);

  useEffect(() => {
    if (!nodeId) return;
    getAffectedNodes(nodeId, projectId).then((result) => {
      if (result.success) {
        setAffectedNodeIds(result.data.affected_node_ids);
      }
      // Non-blocking: failure silently skips highlighting
    });
  }, [nodeId, projectId]);

  const toggleFilter = (type: string) => {
    setFilters((prev) => ({ ...prev, [type]: !prev[type] }));
  };

  const handleExpandModule = useCallback(
    async (moduleId: string) => {
      const result = await getModuleRelationDetail(moduleId, projectId);
      if (result.success) {
        return result.data;
      }
      return { features: [], relations: [] };
    },
    [projectId],
  );

  if (loading) {
    return (
      <div className="text-muted-foreground flex h-[calc(100vh-120px)] items-center justify-center gap-2 text-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        加载关系图中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-[calc(100vh-120px)] items-center justify-center text-sm text-red-500">
        {error}
      </div>
    );
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="text-muted-foreground flex h-[calc(100vh-120px)] flex-col items-center justify-center gap-3">
        <svg
          className="h-16 w-16 opacity-30"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <circle cx="6" cy="6" r="2" />
          <circle cx="18" cy="6" r="2" />
          <circle cx="12" cy="18" r="2" />
          <line x1="8" y1="6" x2="16" y2="6" />
          <line x1="7" y1="8" x2="11" y2="16" />
          <line x1="17" y1="8" x2="13" y2="16" />
        </svg>
        <p className="text-sm">暂无模块关系，请先在功能项中添加关联</p>
      </div>
    );
  }

  const totalNodes = graphData.nodes.length;
  const totalEdges = graphData.edges.length;

  return (
    <div className="space-y-4 px-6 py-4">
      {/* Header with filters and stats */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-semibold">模块关系图</h2>
          <div className="text-muted-foreground flex items-center gap-2 text-sm">
            <span>{totalNodes} 个模块</span>
            <span>&middot;</span>
            <span>{totalEdges} 条关联</span>
            <span>&middot;</span>
            <span>单击选中，双击跳转详情</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {(
            Object.entries(relationTypeConfig) as [
              RelationType,
              (typeof relationTypeConfig)[RelationType],
            ][]
          ).map(([type, config]) => (
            <Button
              key={type}
              variant={filters[type] ? "default" : "outline"}
              size="sm"
              className="gap-1.5"
              onClick={() => toggleFilter(type)}
            >
              <span className={`h-2 w-2 rounded-full ${config.dotClass}`} />
              {config.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="text-muted-foreground flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <svg width="24" height="2">
            <line x1="0" y1="1" x2="24" y2="1" className="stroke-blue-400" strokeWidth="2" />
          </svg>
          <span>depends_on (依赖)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <svg width="24" height="2">
            <line
              x1="0"
              y1="1"
              x2="24"
              y2="1"
              className="stroke-muted-foreground"
              strokeWidth="2"
              strokeDasharray="4 2"
            />
          </svg>
          <span>related_to (相关)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <svg width="24" height="2">
            <line x1="0" y1="1" x2="24" y2="1" className="stroke-red-400" strokeWidth="2" />
          </svg>
          <span>conflicts_with (冲突)</span>
        </div>
      </div>

      {/* Graph */}
      <RelationGraph
        projectId={projectId}
        moduleNodes={graphData.nodes}
        moduleEdges={graphData.edges}
        filters={filters}
        onExpandModule={handleExpandModule}
        affectedNodeIds={affectedNodeIds}
      />
    </div>
  );
}
