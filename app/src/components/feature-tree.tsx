"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { ChevronRight, Folder, FileText, Plus, Pencil, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TreeNode {
  id: string;
  name: string;
  type: "folder" | "file";
  depth: number;
  completionPercent: number;
  children: TreeNode[];
}

function getStatusColor(percent: number) {
  if (percent >= 80) return "bg-green-500";
  if (percent >= 40) return "bg-yellow-500";
  return "bg-red-500";
}

interface FeatureTreeProps {
  data: TreeNode[];
  selectedId: string;
  onSelect: (id: string, type: "folder" | "file") => void;
  onAddChild?: (parentId: string | null, type: "folder" | "file") => void;
  onRename?: (nodeId: string, newName: string) => void;
  onDelete?: (nodeId: string) => void;
  onReorder?: (nodeId: string, newIndex: number) => void;
  onMove?: (nodeId: string, newParentId: string) => void;
}

// ─── Context Menu ─────────────────────────────────────

function ContextMenu({
  x,
  y,
  node,
  onClose,
  onAddChild,
  onRename,
  onDelete,
}: {
  x: number;
  y: number;
  node: TreeNode;
  onClose: () => void;
  onAddChild?: (parentId: string | null, type: "folder" | "file") => void;
  onRename?: (nodeId: string, currentName: string) => void;
  onDelete?: (nodeId: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  return (
    <div
      ref={ref}
      className="bg-popover fixed z-50 min-w-[160px] rounded-md border p-1 shadow-md"
      style={{ left: x, top: y }}
    >
      {node.type === "folder" && (
        <>
          <button
            className="hover:bg-accent flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm"
            onClick={() => {
              onAddChild?.(node.id, "folder");
              onClose();
            }}
          >
            <Folder className="h-4 w-4" /> 添加子文件夹
          </button>
          <button
            className="hover:bg-accent flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm"
            onClick={() => {
              onAddChild?.(node.id, "file");
              onClose();
            }}
          >
            <Plus className="h-4 w-4" /> 添加功能项
          </button>
        </>
      )}
      <button
        className="hover:bg-accent flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm"
        onClick={() => {
          onRename?.(node.id, node.name);
          onClose();
        }}
      >
        <Pencil className="h-4 w-4" /> 重命名
      </button>
      <button
        className="text-destructive hover:bg-accent flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm"
        onClick={() => {
          onDelete?.(node.id);
          onClose();
        }}
      >
        <Trash2 className="h-4 w-4" /> 删除
      </button>
    </div>
  );
}

// ─── Tree Item ────────────────────────────────────────

function TreeItem({
  node,
  level = 0,
  selectedId,
  onSelect,
  onContextMenu,
  onDragStart,
  onDragOver,
  onDrop,
  dragOverId,
  expandedIds,
  toggleExpand,
  editingId,
  editingName,
  onEditingNameChange,
  onEditingConfirm,
  onEditingCancel,
}: {
  node: TreeNode;
  level?: number;
  selectedId: string;
  onSelect: (id: string, type: "folder" | "file") => void;
  onContextMenu: (e: React.MouseEvent, node: TreeNode) => void;
  onDragStart: (nodeId: string) => void;
  onDragOver: (e: React.DragEvent, nodeId: string) => void;
  onDrop: (e: React.DragEvent, targetId: string) => void;
  dragOverId: string | null;
  expandedIds: Set<string>;
  toggleExpand: (id: string) => void;
  editingId: string | null;
  editingName: string;
  onEditingNameChange: (name: string) => void;
  onEditingConfirm: () => void;
  onEditingCancel: () => void;
}) {
  const isFolder = node.type === "folder";
  const isExpanded = expandedIds.has(node.id);
  const isSelected = selectedId === node.id;
  const isDragOver = dragOverId === node.id;
  const isEditing = editingId === node.id;
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  return (
    <div>
      <button
        draggable={!isEditing}
        onDragStart={() => onDragStart(node.id)}
        onDragOver={(e) => onDragOver(e, node.id)}
        onDrop={(e) => onDrop(e, node.id)}
        onClick={() => {
          if (isEditing) return;
          if (isFolder) toggleExpand(node.id);
          onSelect(node.id, node.type);
        }}
        onContextMenu={(e) => onContextMenu(e, node)}
        className={cn(
          "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
          "hover:bg-accent",
          isSelected && "bg-accent font-medium",
          isDragOver && "border-primary border-t-2",
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
        {isEditing ? (
          <input
            ref={inputRef}
            className="bg-background focus:ring-ring flex-1 rounded border px-1 py-0.5 text-sm outline-none focus:ring-1"
            value={editingName}
            onChange={(e) => onEditingNameChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onEditingConfirm();
              if (e.key === "Escape") onEditingCancel();
            }}
            onBlur={onEditingConfirm}
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className="flex-1 truncate text-left">{node.name}</span>
        )}
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
              onContextMenu={onContextMenu}
              onDragStart={onDragStart}
              onDragOver={onDragOver}
              onDrop={onDrop}
              dragOverId={dragOverId}
              expandedIds={expandedIds}
              toggleExpand={toggleExpand}
              editingId={editingId}
              editingName={editingName}
              onEditingNameChange={onEditingNameChange}
              onEditingConfirm={onEditingConfirm}
              onEditingCancel={onEditingCancel}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Feature Tree ─────────────────────────────────────

// ─── Empty Area Context Menu ─────────────────────────

function RootContextMenu({
  x,
  y,
  onClose,
  onAddChild,
}: {
  x: number;
  y: number;
  onClose: () => void;
  onAddChild?: (parentId: string | null, type: "folder" | "file") => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  return (
    <div
      ref={ref}
      className="bg-popover fixed z-50 min-w-[160px] rounded-md border p-1 shadow-md"
      style={{ left: x, top: y }}
    >
      <button
        className="hover:bg-accent flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm"
        onClick={() => {
          onAddChild?.(null, "folder");
          onClose();
        }}
      >
        <Folder className="h-4 w-4" /> 添加顶层文件夹
      </button>
      <button
        className="hover:bg-accent flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm"
        onClick={() => {
          onAddChild?.(null, "file");
          onClose();
        }}
      >
        <Plus className="h-4 w-4" /> 添加顶层功能项
      </button>
    </div>
  );
}

export function FeatureTree({
  data,
  selectedId,
  onSelect,
  onAddChild,
  onRename,
  onDelete,
  onReorder,
  onMove,
}: FeatureTreeProps) {
  const allFolderIds = new Set<string>();
  function collectFolders(nodes: TreeNode[]) {
    for (const n of nodes) {
      if (n.type === "folder") {
        allFolderIds.add(n.id);
        collectFolders(n.children);
      }
    }
  }
  collectFolders(data);

  const [expandedIds, setExpandedIds] = useState<Set<string>>(allFolderIds);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; node: TreeNode } | null>(
    null,
  );
  const [rootContextMenu, setRootContextMenu] = useState<{ x: number; y: number } | null>(null);
  const [dragNodeId, setDragNodeId] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);

  // Inline rename state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");

  const handleDragStart = (nodeId: string) => setDragNodeId(nodeId);
  const handleDragOver = (e: React.DragEvent, nodeId: string) => {
    e.preventDefault();
    setDragOverId(nodeId);
  };
  const handleDrop = (e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    setDragOverId(null);
    if (!dragNodeId || dragNodeId === targetId) return;

    // Find target node to check if it's a folder (cross-level move)
    function findNode(nodes: TreeNode[], id: string): TreeNode | null {
      for (const n of nodes) {
        if (n.id === id) return n;
        const found = findNode(n.children, id);
        if (found) return found;
      }
      return null;
    }
    // Check if dragNode is ancestor of target (prevent moving into own descendant)
    function isAncestor(nodes: TreeNode[], ancestorId: string, descendantId: string): boolean {
      const ancestor = findNode(nodes, ancestorId);
      if (!ancestor) return false;
      function check(node: TreeNode): boolean {
        if (node.id === descendantId) return true;
        return node.children.some(check);
      }
      return check(ancestor);
    }

    const targetNode = findNode(data, targetId);
    if (targetNode?.type === "folder" && !isAncestor(data, dragNodeId, targetId)) {
      // Cross-level move: drop onto a folder
      onMove?.(dragNodeId, targetId);
    } else {
      // Same-level reorder
      function findIndex(nodes: TreeNode[], id: string): number {
        for (let i = 0; i < nodes.length; i++) {
          if (nodes[i].id === id) return i;
          const found = findIndex(nodes[i].children, id);
          if (found >= 0) return found;
        }
        return -1;
      }
      const targetIndex = findIndex(data, targetId);
      if (targetIndex >= 0) onReorder?.(dragNodeId, targetIndex);
    }
    setDragNodeId(null);
  };

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleContextMenu = (e: React.MouseEvent, node: TreeNode) => {
    e.preventDefault();
    setRootContextMenu(null);
    setContextMenu({ x: e.clientX, y: e.clientY, node });
  };

  const handleEmptyAreaContextMenu = (e: React.MouseEvent) => {
    // Only show if right-click is on the empty area (not on a tree node)
    if ((e.target as HTMLElement).closest("button[draggable]")) return;
    e.preventDefault();
    setContextMenu(null);
    setRootContextMenu({ x: e.clientX, y: e.clientY });
  };

  const handleStartRename = useCallback((nodeId: string, currentName: string) => {
    setEditingId(nodeId);
    setEditingName(currentName);
  }, []);

  const handleConfirmRename = useCallback(() => {
    if (editingId && editingName.trim()) {
      onRename?.(editingId, editingName.trim());
    }
    setEditingId(null);
    setEditingName("");
  }, [editingId, editingName, onRename]);

  const handleCancelRename = useCallback(() => {
    setEditingId(null);
    setEditingName("");
  }, []);

  return (
    <div className="min-h-[100px] space-y-1 py-2" onContextMenu={handleEmptyAreaContextMenu}>
      {data.map((node) => (
        <TreeItem
          key={node.id}
          node={node}
          selectedId={selectedId}
          onSelect={onSelect}
          onContextMenu={handleContextMenu}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          dragOverId={dragOverId}
          expandedIds={expandedIds}
          toggleExpand={toggleExpand}
          editingId={editingId}
          editingName={editingName}
          onEditingNameChange={setEditingName}
          onEditingConfirm={handleConfirmRename}
          onEditingCancel={handleCancelRename}
        />
      ))}
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          node={contextMenu.node}
          onClose={() => setContextMenu(null)}
          onAddChild={onAddChild}
          onRename={handleStartRename}
          onDelete={onDelete}
        />
      )}
      {rootContextMenu && (
        <RootContextMenu
          x={rootContextMenu.x}
          y={rootContextMenu.y}
          onClose={() => setRootContextMenu(null)}
          onAddChild={onAddChild}
        />
      )}
    </div>
  );
}
