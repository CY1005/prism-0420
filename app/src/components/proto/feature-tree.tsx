"use client";

import { useState, useEffect } from "react";
import { ChevronRight, Folder, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TreeNode {
  id: string;
  name: string;
  type: "folder" | "file";
  completionPercent?: number;
  children?: TreeNode[];
}

interface FeatureTreeProps {
  data: TreeNode[];
  selectedId: string;
  onSelect: (id: string) => void;
  defaultExpanded?: string[];
}

function getStatusColor(percent?: number) {
  if (percent === undefined) return "bg-muted-foreground";
  if (percent >= 80) return "bg-green-500";
  if (percent >= 40) return "bg-yellow-500";
  return "bg-red-500";
}

function TreeItem({
  node,
  level = 0,
  selectedId,
  onSelect,
  expandedIds,
  toggleExpand,
}: {
  node: TreeNode;
  level?: number;
  selectedId: string;
  onSelect: (id: string) => void;
  expandedIds: Set<string>;
  toggleExpand: (id: string) => void;
}) {
  const isFolder = node.type === "folder";
  const isExpanded = expandedIds.has(node.id);
  const isSelected = selectedId === node.id;

  return (
    <div>
      <button
        onClick={() => {
          if (isFolder) {
            toggleExpand(node.id);
          } else {
            onSelect(node.id);
          }
        }}
        className={cn(
          "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
          "hover:bg-accent",
          isSelected && !isFolder && "bg-accent text-accent-foreground font-medium",
        )}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
      >
        {isFolder ? (
          <ChevronRight
            className={cn(
              "text-muted-foreground h-4 w-4 shrink-0 transition-transform",
              isExpanded && "rotate-90",
            )}
          />
        ) : (
          <span className="w-4" />
        )}
        {isFolder ? (
          <Folder className="text-primary h-4 w-4 shrink-0" />
        ) : (
          <FileText className="text-muted-foreground h-4 w-4 shrink-0" />
        )}
        <span className="flex-1 truncate text-left">{node.name}</span>
        <span
          className={cn("h-2 w-2 shrink-0 rounded-full", getStatusColor(node.completionPercent))}
        />
      </button>
      {isFolder && isExpanded && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeItem
              key={child.id}
              node={child}
              level={level + 1}
              selectedId={selectedId}
              onSelect={onSelect}
              expandedIds={expandedIds}
              toggleExpand={toggleExpand}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function ProtoFeatureTree({
  data,
  selectedId,
  onSelect,
  defaultExpanded,
}: FeatureTreeProps) {
  const [mounted, setMounted] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    setExpandedIds(
      new Set(
        defaultExpanded || [
          "private-cloud",
          "inference-service",
          "training-service",
          "smart-computing",
        ],
      ),
    );
    setMounted(true);
  }, [defaultExpanded]);

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  if (!mounted) {
    return <div className="space-y-1 py-2" />;
  }

  return (
    <div className="space-y-1 py-2">
      {data.map((node) => (
        <TreeItem
          key={node.id}
          node={node}
          selectedId={selectedId}
          onSelect={onSelect}
          expandedIds={expandedIds}
          toggleExpand={toggleExpand}
        />
      ))}
    </div>
  );
}
