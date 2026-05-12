"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
  type FitViewOptions,
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

interface ModuleNode {
  id: string;
  name: string;
  featureCount: number;
  completionPercent: number;
}

interface ModuleEdge {
  sourceModuleId: string;
  targetModuleId: string;
  relationType: string;
  count: number;
}

// Phase 2.3 cleanup D: 使用 actions/relations 的类型，避免双定义冲突
// （之前 component 里 FeatureRelation.id 写成 number，跟后端 string 漂移）
import type { FeatureNode, FeatureRelation } from "@/actions/relations";

export interface RelationGraphProps {
  projectId: string;
  moduleNodes: ModuleNode[];
  moduleEdges: ModuleEdge[];
  filters: Record<string, boolean>;
  onExpandModule?: (
    moduleId: string,
  ) => Promise<{ features: FeatureNode[]; relations: FeatureRelation[] }>;
  affectedNodeIds?: string[];
}

function completionToColor(percent: number): string {
  if (percent >= 80) return "#dcfce7";
  if (percent >= 40) return "#fef9c3";
  return "#fee2e2";
}

function completionToBorder(percent: number): string {
  if (percent >= 80) return "#86efac";
  if (percent >= 40) return "#fde047";
  return "#fca5a5";
}

const edgeStyleMap: Record<
  string,
  { stroke: string; strokeDasharray?: string; animated?: boolean }
> = {
  depends_on: { stroke: "#3b82f6", animated: true },
  related_to: { stroke: "#94a3b8", strokeDasharray: "6 3" },
  conflicts_with: { stroke: "#ef4444" },
};

function computeCircularLayout(
  nodeIds: string[],
  radiusBase: number = 220,
): Record<string, { x: number; y: number }> {
  const count = nodeIds.length;
  const radius = Math.max(radiusBase, count * 45);
  const positions: Record<string, { x: number; y: number }> = {};
  nodeIds.forEach((id, i) => {
    const angle = (2 * Math.PI * i) / count - Math.PI / 2;
    positions[id] = {
      x: radius * Math.cos(angle) + radius + 100,
      y: radius * Math.sin(angle) + radius + 100,
    };
  });
  return positions;
}

const fitViewOptions: FitViewOptions = { padding: 0.2 };

export function RelationGraph({
  projectId,
  moduleNodes: modules,
  moduleEdges: modEdges,
  filters,
  onExpandModule,
  affectedNodeIds = [],
}: RelationGraphProps) {
  const router = useRouter();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [expandedModuleId, setExpandedModuleId] = useState<string | null>(null);
  const [expandedFeatures, setExpandedFeatures] = useState<FeatureNode[]>([]);
  const [expandedRelations, setExpandedRelations] = useState<FeatureRelation[]>([]);

  // Build React Flow nodes for modules
  const positions = useMemo(() => computeCircularLayout(modules.map((m) => m.id)), [modules]);

  const affectedSet = useMemo(() => new Set(affectedNodeIds), [affectedNodeIds]);

  const rfNodes: Node[] = useMemo(() => {
    const nodes: Node[] = modules.map((mod) => {
      const isAffected = affectedSet.has(mod.id);
      return {
        id: mod.id,
        position: positions[mod.id] ?? { x: 0, y: 0 },
        data: { label: mod.name },
        style: {
          background: completionToColor(mod.completionPercent),
          border: isAffected
            ? "2px solid #fb923c"
            : `2px solid ${completionToBorder(mod.completionPercent)}`,
          borderRadius: 8,
          padding: "8px 14px",
          fontSize: 13,
          fontWeight: 600,
          whiteSpace: "nowrap" as const,
          opacity: selectedNodeId && selectedNodeId !== mod.id ? 0.3 : 1,
          cursor: "pointer",
          boxShadow: isAffected ? "0 0 0 2px #fb923c, 0 0 8px 2px rgba(251,146,60,0.4)" : undefined,
        },
      };
    });

    // Add expanded feature nodes around the expanded module
    if (expandedModuleId && expandedFeatures.length > 0) {
      const parentPos = positions[expandedModuleId];
      if (parentPos) {
        const featureRadius = 120;
        expandedFeatures.forEach((feat, i) => {
          const angle = (2 * Math.PI * i) / expandedFeatures.length;
          const isAffected = affectedSet.has(feat.id);
          nodes.push({
            id: feat.id,
            position: {
              x: parentPos.x + featureRadius * Math.cos(angle),
              y: parentPos.y + featureRadius * Math.sin(angle) + 50,
            },
            data: { label: feat.name },
            style: {
              background: completionToColor(feat.completionPercent),
              border: isAffected
                ? "2px solid #fb923c"
                : `1px solid ${completionToBorder(feat.completionPercent)}`,
              borderRadius: 6,
              padding: "4px 10px",
              fontSize: 11,
              fontWeight: 400,
              whiteSpace: "nowrap" as const,
              opacity: selectedNodeId && selectedNodeId !== feat.id ? 0.3 : 1,
              cursor: "pointer",
              boxShadow: isAffected
                ? "0 0 0 2px #fb923c, 0 0 8px 2px rgba(251,146,60,0.4)"
                : undefined,
            },
          });
        });
      }
    }

    return nodes;
  }, [modules, positions, selectedNodeId, expandedModuleId, expandedFeatures, affectedSet]);

  // Build React Flow edges
  const rfEdges: Edge[] = useMemo(() => {
    const edges: Edge[] = [];

    // Module-level edges
    modEdges.forEach((e, i) => {
      if (!filters[e.relationType]) return;
      const style = edgeStyleMap[e.relationType] ?? edgeStyleMap.related_to;
      const isHighlighted =
        selectedNodeId &&
        (e.sourceModuleId === selectedNodeId || e.targetModuleId === selectedNodeId);
      edges.push({
        id: `mod-${i}`,
        source: e.sourceModuleId,
        target: e.targetModuleId,
        label: e.count > 1 ? `${e.count}` : undefined,
        labelStyle: { fontSize: 10, fill: "#64748b" },
        labelBgStyle: { fill: "#f8fafc", fillOpacity: 0.8 },
        style: {
          stroke: style.stroke,
          strokeDasharray: style.strokeDasharray,
          opacity: selectedNodeId ? (isHighlighted ? 1 : 0.1) : 0.7,
          strokeWidth: isHighlighted ? 2.5 : 1.5,
        },
        animated: style.animated,
      });
    });

    // Feature-level cross-module edges
    if (expandedModuleId && expandedRelations.length > 0) {
      expandedRelations.forEach((rel) => {
        if (!filters[rel.relationType]) return;
        const style = edgeStyleMap[rel.relationType] ?? edgeStyleMap.related_to;
        edges.push({
          id: `feat-${rel.id}`,
          source: rel.sourceNodeId,
          target: rel.targetNodeId,
          style: {
            stroke: style.stroke,
            strokeDasharray: style.strokeDasharray,
            strokeWidth: 1.5,
          },
          animated: style.animated,
        });
      });
    }

    return edges;
  }, [modEdges, filters, selectedNodeId, expandedModuleId, expandedRelations]);

  const onNodeClick: NodeMouseHandler = useCallback(
    async (_event, node) => {
      // Toggle selection
      if (selectedNodeId === node.id) {
        setSelectedNodeId(null);
        return;
      }
      setSelectedNodeId(node.id);

      // If this is a module node, offer expand
      const isModule = modules.some((m) => m.id === node.id);
      if (isModule && onExpandModule) {
        if (expandedModuleId === node.id) {
          // Collapse
          setExpandedModuleId(null);
          setExpandedFeatures([]);
          setExpandedRelations([]);
        } else {
          const result = await onExpandModule(node.id);
          setExpandedModuleId(node.id);
          setExpandedFeatures(result.features);
          setExpandedRelations(result.relations);
        }
      }
    },
    [selectedNodeId, modules, onExpandModule, expandedModuleId],
  );

  const onNodeDoubleClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      // Navigate to feature or module profile on double-click
      const isModule = modules.some((m) => m.id === node.id);
      if (isModule) {
        router.push(`/projects/${projectId}/modules/${node.id}`);
      } else {
        router.push(`/projects/${projectId}/features/${node.id}`);
      }
    },
    [modules, projectId, router],
  );

  return (
    <div className="h-[calc(100vh-320px)] min-h-[400px] w-full">
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodeClick={onNodeClick}
        onNodeDoubleClick={onNodeDoubleClick}
        fitView
        fitViewOptions={fitViewOptions}
        attributionPosition="bottom-right"
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
