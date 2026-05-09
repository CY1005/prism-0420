"use client";

import { useState, useTransition, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  PanelLeftClose,
  PanelLeft,
  ChevronRight,
  Folder,
  FileText,
  Plus,
  Users,
  Server,
  GitBranch,
  Lightbulb,
  TestTube,
  ClipboardList,
  Building,
  Upload,
  Sparkles,
  BookOpen,
  Loader2,
  Download,
  Settings,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { FeatureTree, type TreeNode } from "@/components/feature-tree";
import { DimensionCard } from "@/components/dimension-card";
import { VersionTimeline, type VersionRecord } from "@/components/version-timeline";
import { SnapshotResult, type SnapshotData } from "@/components/snapshot-result";
import { cn } from "@/lib/utils";
import {
  getNodeWithDimensions,
  getFolderOverview,
  createNode,
  createDimensionRecord,
  updateDimensionRecord,
  deleteDimensionRecord,
  renameNode,
  deleteNode,
  updateNodeSortOrder,
  getNodeDescendantCount,
  moveNode,
} from "@/actions/nodes";
import { createVersion } from "@/actions/versions";
import { createIssue, getIssuesByNode, deleteIssue } from "@/actions/issues";
import { getCompetitorsByProject, createCompetitor } from "@/actions/competitors";
import {
  createReference,
  updateReference,
  deleteReference,
  getReferencesByNode,
} from "@/actions/competitor-references";
import { createRelation } from "@/actions/relations";
import { getFeedItemsByNode } from "@/actions/feed";
import { exportNodes, exportProject } from "@/actions/export";
import { FeedList, type FeedItemData } from "@/components/feed-card";
import {
  CompetitorReferenceList,
  AddReferenceDialog,
  type Competitor,
  type CompetitorReference,
} from "@/components/competitor-reference-card";
import {
  IssueList,
  AddIssueDialog,
  CATEGORY_DIMENSION_MAP,
  type Issue,
  type IssueCategory,
} from "@/components/issue-card";
import { Separator } from "@/components/ui/separator";

// ─── Icon Mapping ───────────────────────────────────────
const dimensionIconMap: Record<string, LucideIcon> = {
  description: FileText,
  user_scenario: Users,
  tech_impl: Server,
  design_decision: GitBranch,
  engineering_exp: Lightbulb,
  test_analysis: TestTube,
  requirement_analysis: ClipboardList,
  competitive_ref: Building,
};

type Project = {
  id: string;
  name: string;
  templateType: string;
  hierarchyLabels: string[];
  versionMode: string;
};

type DimensionConfig = {
  config: { id: number; dimensionTypeId: number; sortOrder: number };
  dimType: {
    id: number;
    key: string;
    name: string;
    icon: string;
    description: string | null;
    fieldSchema: Record<string, unknown> | null;
  };
};

type NodeData = {
  node: { id: string; name: string; parentId: string | null; path: string; [key: string]: unknown };
  records: {
    record: {
      id: string;
      dimensionTypeId: number;
      content: Record<string, unknown>;
      [key: string]: unknown;
    };
    dimType: { id: number; key: string; name: string; [key: string]: unknown };
  }[];
  versions: {
    id: string;
    versionLabel: string;
    summary: string;
    isCurrent?: boolean;
    [key: string]: unknown;
  }[];
};

type FolderChild = {
  id: string;
  name: string;
  type: string;
  filledDimensions: number;
  totalDimensions: number;
  completionPercent: number;
  childCount?: number;
};

interface WorkspaceProps {
  project: Project;
  tree: TreeNode[];
  dimensions: DimensionConfig[];
  initialNodeData: NodeData | null;
  initialSelectedId: string | null;
}

// ─── Dimension Content Renderers ────────────────────────

function renderDimensionContent(key: string, content: Record<string, unknown>) {
  switch (key) {
    case "description":
      return <p className="text-sm leading-relaxed">{content.text as string}</p>;

    case "user_scenario": {
      const scenarios = content.scenarios as
        | { role: string; scenario: string; techStack: string[] }[]
        | undefined;
      if (!Array.isArray(scenarios))
        return <p className="text-sm">{(content.text as string) ?? JSON.stringify(content)}</p>;
      return (
        <div className="overflow-hidden rounded-md border">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50">
                <th className="px-3 py-2 text-left font-medium">角色</th>
                <th className="px-3 py-2 text-left font-medium">使用场景</th>
                <th className="px-3 py-2 text-left font-medium">技术栈</th>
              </tr>
            </thead>
            <tbody>
              {scenarios.map((s, i) => (
                <tr key={i} className="border-t">
                  <td className="px-3 py-2 font-medium">{s.role}</td>
                  <td className="px-3 py-2">{s.scenario}</td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {s.techStack.map((t) => (
                        <Badge key={t} variant="outline" className="text-xs">
                          {t}
                        </Badge>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    case "tech_impl": {
      const entries = content.entries as
        | { title: string; text: string; tags: string[] }[]
        | undefined;
      if (!Array.isArray(entries))
        return <p className="text-sm">{(content.text as string) ?? JSON.stringify(content)}</p>;
      const ref = content.referenceStandards as string | undefined;
      return (
        <div className="space-y-3">
          {entries.map((entry, i) => (
            <div key={i} className="bg-muted/30 rounded-md border p-4">
              <h4 className="text-sm font-medium">{entry.title}</h4>
              <p className="text-muted-foreground mt-1 text-sm">{entry.text}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                {entry.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
          {ref && <p className="text-muted-foreground text-xs">参考标准：{ref}</p>}
        </div>
      );
    }

    case "design_decision": {
      const labels: Record<string, string> = {
        context: "背景",
        decision: "决策",
        alternatives: "放弃的方案",
        consequences: "后果",
      };
      return (
        <div className="space-y-3 rounded-md border p-4">
          {Object.entries(labels).map(([field, label]) => (
            <div key={field}>
              <h4
                className={cn(
                  "text-xs font-medium tracking-wider uppercase",
                  field === "alternatives" ? "text-destructive" : "text-muted-foreground",
                )}
              >
                {label}
              </h4>
              <p
                className={cn(
                  "mt-1 text-sm",
                  field === "alternatives" ? "text-muted-foreground" : "",
                )}
              >
                {content[field] as string}
              </p>
            </div>
          ))}
        </div>
      );
    }

    case "engineering_exp":
      return (
        <div className="rounded-md border bg-amber-50/50 p-4">
          <h4 className="text-sm font-medium">{content.title as string}</h4>
          <p className="text-muted-foreground mt-1 text-sm">{content.text as string}</p>
          {Array.isArray(content.tags) && (
            <div className="mt-2 flex flex-wrap gap-1">
              {(content.tags as string[]).map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </div>
      );

    default:
      return (
        <pre className="text-muted-foreground text-xs whitespace-pre-wrap">
          {JSON.stringify(content, null, 2)}
        </pre>
      );
  }
}

function buildBreadcrumb(tree: TreeNode[], nodeId: string): TreeNode[] {
  const path: TreeNode[] = [];
  function find(nodes: TreeNode[], target: string): boolean {
    for (const n of nodes) {
      path.push(n);
      if (n.id === target) return true;
      if (n.children.length > 0 && find(n.children, target)) return true;
      path.pop();
    }
    return false;
  }
  find(tree, nodeId);
  return path;
}

function getStatusColor(percent: number) {
  if (percent >= 80) return "bg-green-500";
  if (percent >= 40) return "bg-yellow-500";
  return "bg-red-500";
}

// ─── Main Workspace ─────────────────────────────────────

export function ProjectWorkspace({
  project,
  tree: initialTree,
  dimensions,
  initialNodeData,
  initialSelectedId,
}: WorkspaceProps) {
  const router = useRouter();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedId, setSelectedId] = useState(initialSelectedId ?? "");
  const [selectedType, setSelectedType] = useState<"folder" | "file">("file");
  const [nodeData, setNodeData] = useState<NodeData | null>(initialNodeData);
  const [folderChildren, setFolderChildren] = useState<FolderChild[] | null>(null);
  const [isPending, startTransition] = useTransition();
  const [tree, setTree] = useState(initialTree);

  // Dialog states
  const [addNodeDialog, setAddNodeDialog] = useState(false);
  const [addNodeParentId, setAddNodeParentId] = useState<string | null>(null);
  const [addNodeType, setAddNodeType] = useState<"folder" | "file">("file");
  const [addNodeName, setAddNodeName] = useState("");

  // Delete confirmation dialog
  const [deleteDialog, setDeleteDialog] = useState(false);
  const [deleteNodeId, setDeleteNodeId] = useState("");
  const [deleteDescendantInfo, setDeleteDescendantInfo] = useState<{
    childNodeCount: number;
    dimensionRecordCount: number;
  } | null>(null);

  const [addDimDialog, setAddDimDialog] = useState(false);
  const [addDimTypeId, setAddDimTypeId] = useState(0);
  const [addDimTypeName, setAddDimTypeName] = useState("");
  const [addDimContent, setAddDimContent] = useState("");

  const [editDimDialog, setEditDimDialog] = useState(false);
  const [editDimRecordId, setEditDimRecordId] = useState("");
  const [editDimContent, setEditDimContent] = useState("");

  // F7: Issue states
  const [nodeIssues, setNodeIssues] = useState<Issue[]>([]);
  const [addIssueDialog, setAddIssueDialog] = useState(false);

  // F6: Competitor reference states
  const [nodeRefs, setNodeRefs] = useState<CompetitorReference[]>([]);
  const [projectCompetitors, setProjectCompetitors] = useState<Competitor[]>([]);
  const [addRefDialog, setAddRefDialog] = useState(false);
  const [editingRef, setEditingRef] = useState<CompetitorReference | null>(null);

  // F14: Feed items linked to this node
  const [nodeFeedItems, setNodeFeedItems] = useState<FeedItemData[]>([]);

  // F8: Relation states
  const [addRelationDialog, setAddRelationDialog] = useState(false);
  const [relationTargetId, setRelationTargetId] = useState("");
  const [relationType, setRelationType] = useState("depends_on");
  const [relationSaving, setRelationSaving] = useState(false);

  // Aha Moment state (F11 AC5/AC6)
  const searchParams = useSearchParams();
  const [importBanner, setImportBanner] = useState<{
    count: number;
    moduleName: string;
  } | null>(null);

  // First-project detection: tree has no root nodes
  const isEmptyProject = tree.length === 0;

  // Panorama prompt after first dimension record saved
  const [showPanoramaPrompt, setShowPanoramaPrompt] = useState(false);

  // F19: Export states
  const [exporting, setExporting] = useState(false);

  // F16: Snapshot states
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [snapshotData, setSnapshotData] = useState<SnapshotData | null>(null);
  const [showSnapshotDialog, setShowSnapshotDialog] = useState(false);

  // Detect import redirect and auto-navigate to top module
  useEffect(() => {
    const imported = searchParams.get("imported");
    const topModule = searchParams.get("topModule");
    const count = searchParams.get("count");

    if (imported === "true" && topModule) {
      // Find the module node in tree
      function findNode(nodes: TreeNode[], id: string): TreeNode | null {
        for (const n of nodes) {
          if (n.id === id) return n;
          const found = findNode(n.children, id);
          if (found) return found;
        }
        return null;
      }
      const moduleNode = findNode(initialTree, topModule);
      if (moduleNode) {
        handleSelectNode(topModule, moduleNode.type);
        setImportBanner({
          count: count ? parseInt(count) : 0,
          moduleName: moduleNode.name,
        });
      }

      // Clean up URL params without navigation
      window.history.replaceState({}, "", `/projects/${project.id}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ─── Handlers ───────────────────────────────────────

  const refreshPage = () => router.refresh();

  // F16: Generate snapshot
  const handleGenerateSnapshot = async () => {
    if (!nodeData) return;
    setSnapshotLoading(true);
    try {
      const res = await fetch("/api/snapshot/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ node_id: nodeData.node.id, project_id: project.id }),
      });
      if (res.ok) {
        const result = await res.json();
        setSnapshotData(result);
        setShowSnapshotDialog(true);
      }
    } finally {
      setSnapshotLoading(false);
    }
  };

  // F16: Save snapshot
  const handleSaveSnapshot = async (params: {
    summary: string;
    selectedDimensions: { dimensionKey: string; content: string }[];
  }) => {
    if (!nodeData) return;
    await fetch("/api/snapshot/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        node_id: nodeData.node.id,
        project_id: project.id,
        summary: params.summary,
        dimensions: params.selectedDimensions.map((d) => ({
          dimension_type_key: d.dimensionKey,
          content: { text: d.content },
        })),
      }),
    });
    setShowSnapshotDialog(false);
    setSnapshotData(null);
    // Refresh node data
    const data = await getNodeWithDimensions(nodeData.node.id);
    setNodeData(data);
    refreshPage();
  };

  // F19: Export node as Markdown
  const handleExportNode = async () => {
    if (!nodeData) return;
    setExporting(true);
    try {
      const result = await exportNodes(project.id, [nodeData.node.id]);
      if (result.success) {
        const blob = new Blob([result.data.content], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = result.data.filename;
        a.click();
        URL.revokeObjectURL(url);
      }
    } finally {
      setExporting(false);
    }
  };

  // F19: Export module as ZIP
  const handleExportModule = async () => {
    if (!selectedId) return;
    setExporting(true);
    try {
      const result = await exportProject(project.id, selectedId);
      if (result.success) {
        const binary = atob(result.data.content);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: "application/zip" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = result.data.filename;
        a.click();
        URL.revokeObjectURL(url);
      }
    } finally {
      setExporting(false);
    }
  };

  const handleSelectNode = (id: string, type: "folder" | "file") => {
    setSelectedId(id);
    setSelectedType(type);
    startTransition(async () => {
      if (type === "file") {
        setFolderChildren(null);
        const [data, issues, refs, comps, feedLinked] = await Promise.all([
          getNodeWithDimensions(id),
          getIssuesByNode(project.id, id),
          getReferencesByNode(project.id, id),
          getCompetitorsByProject(project.id),
          getFeedItemsByNode(project.id, id),
        ]);
        setNodeData(data);
        setNodeIssues(issues as Issue[]);
        setNodeRefs(refs as CompetitorReference[]);
        setProjectCompetitors(comps as Competitor[]);
        setNodeFeedItems(feedLinked as FeedItemData[]);
      } else {
        setNodeData(null);
        setNodeIssues([]);
        setNodeRefs([]);
        setNodeFeedItems([]);
        const children = await getFolderOverview(id, project.id);
        setFolderChildren(children);
      }
    });
  };

  const handleAddChild = (parentId: string | null, type: "folder" | "file") => {
    setAddNodeParentId(parentId);
    setAddNodeType(type);
    setAddNodeName("");
    setAddNodeDialog(true);
  };

  const handleConfirmAddNode = () => {
    if (!addNodeName.trim()) return;
    startTransition(async () => {
      try {
        const result = await createNode({
          projectId: project.id,
          parentId: addNodeParentId,
          name: addNodeName.trim(),
          type: addNodeType,
        });
        if (!result.success) {
          alert(`创建失败: ${result.error}`);
          return;
        }
        setAddNodeDialog(false);
        refreshPage();
      } catch (e) {
        alert(`创建失败: ${e instanceof Error ? e.message : "未知错误"}`);
      }
    });
  };

  const handleRename = (nodeId: string, newName: string) => {
    startTransition(async () => {
      await renameNode({ nodeId, name: newName });
      refreshPage();
    });
  };

  const handleDelete = (nodeId: string) => {
    setDeleteNodeId(nodeId);
    startTransition(async () => {
      const info = await getNodeDescendantCount(nodeId);
      setDeleteDescendantInfo(info);
      setDeleteDialog(true);
    });
  };

  const handleConfirmDelete = () => {
    startTransition(async () => {
      // Find parent node for auto-selection after delete (F3 AC14)
      let parentId: string | null = null;
      if (selectedId === deleteNodeId) {
        function findParent(nodes: TreeNode[], targetId: string): string | null {
          for (const n of nodes) {
            for (const child of n.children) {
              if (child.id === targetId) return n.id;
              const found = findParent([child], targetId);
              if (found) return found;
            }
          }
          return null;
        }
        parentId = findParent(tree, deleteNodeId);
      }

      await deleteNode({ nodeId: deleteNodeId });

      if (selectedId === deleteNodeId) {
        if (parentId) {
          handleSelectNode(parentId, "folder");
        } else {
          setSelectedId("");
          setNodeData(null);
          setFolderChildren(null);
        }
      }
      setDeleteDialog(false);
      setDeleteDescendantInfo(null);
      refreshPage();
    });
  };

  const handleAddDimension = (dimTypeId: number, dimTypeName: string) => {
    setAddDimTypeId(dimTypeId);
    setAddDimTypeName(dimTypeName);
    setAddDimContent("");
    setAddDimDialog(true);
  };

  const handleConfirmAddDimension = () => {
    if (!addDimContent.trim() || !nodeData) return;
    startTransition(async () => {
      let content: Record<string, unknown>;
      try {
        content = JSON.parse(addDimContent);
      } catch {
        content = { text: addDimContent };
      }
      // Check if project had zero dimension records before this save
      const hadNoRecords = nodeData.records.length === 0;
      await createDimensionRecord({
        nodeId: nodeData.node.id,
        dimensionTypeId: addDimTypeId,
        content,
      });
      setAddDimDialog(false);
      const data = await getNodeWithDimensions(nodeData.node.id);
      setNodeData(data);
      if (hadNoRecords && data && data.records.length > 0) {
        setShowPanoramaPrompt(true);
      }
      refreshPage();
    });
  };

  const handleEditDimension = (recordId: string, content: Record<string, unknown>) => {
    setEditDimRecordId(recordId);
    const text = content.text as string | undefined;
    setEditDimContent(text ?? JSON.stringify(content, null, 2));
    setEditDimDialog(true);
  };

  const handleConfirmEditDimension = () => {
    if (!editDimContent.trim() || !nodeData) return;
    startTransition(async () => {
      let content: Record<string, unknown>;
      try {
        content = JSON.parse(editDimContent);
      } catch {
        content = { text: editDimContent };
      }
      // Pass actual record version for optimistic locking
      const currentRecord = nodeData.records.find((r) => r.record.id === editDimRecordId);
      const currentVersion =
        ((currentRecord?.record as Record<string, unknown>)?.version as number) ?? 1;
      await updateDimensionRecord(editDimRecordId, content, currentVersion);
      setEditDimDialog(false);
      const data = await getNodeWithDimensions(nodeData.node.id);
      setNodeData(data);
    });
  };

  const handleReorder = (nodeId: string, newIndex: number) => {
    startTransition(async () => {
      await updateNodeSortOrder(nodeId, newIndex);
      refreshPage();
    });
  };

  const handleMove = (nodeId: string, newParentId: string) => {
    startTransition(async () => {
      await moveNode(nodeId, newParentId);
      refreshPage();
    });
  };

  const handleDeleteDimension = (recordId: string) => {
    if (!confirm("确定删除此记录？")) return;
    startTransition(async () => {
      await deleteDimensionRecord(recordId);
      if (nodeData) {
        const data = await getNodeWithDimensions(nodeData.node.id);
        setNodeData(data);
      }
      refreshPage();
    });
  };

  const handleCreateVersion = (data: {
    versionLabel: string;
    summary: string;
    changeType: string;
    details?: string;
  }) => {
    if (!nodeData) return;
    startTransition(async () => {
      await createVersion(
        nodeData.node.id,
        data.versionLabel,
        data.summary,
        data.changeType,
        data.details,
      );
      const updated = await getNodeWithDimensions(nodeData.node.id);
      setNodeData(updated);
      refreshPage();
    });
  };

  // ─── F7: Issue Handlers ─────────────────────────────────

  const handleAddIssue = (data: { category: string; description: string; tags: string[] }) => {
    if (!nodeData) return;
    startTransition(async () => {
      const result = await createIssue({
        projectId: project.id,
        nodeId: nodeData.node.id,
        category: data.category as "bug" | "tech_debt" | "design_flaw" | "performance",
        description: data.description,
        tags: data.tags,
      });
      if (result.success) {
        const issues = await getIssuesByNode(project.id, nodeData.node.id);
        setNodeIssues(issues as Issue[]);
      }
    });
  };

  const handleDeleteIssue = (issueId: string) => {
    if (!confirm("确定删除此问题？")) return;
    startTransition(async () => {
      const result = await deleteIssue(issueId);
      if (result.success && nodeData) {
        const issues = await getIssuesByNode(project.id, nodeData.node.id);
        setNodeIssues(issues as Issue[]);
      }
    });
  };

  // ─── F6: Competitor Reference Handlers ──────────────────

  const handleCreateCompetitorInline = async (data: {
    name: string;
    website?: string;
    description?: string;
  }): Promise<string | null> => {
    const result = await createCompetitor({ projectId: project.id, ...data });
    if (result.success) {
      const comps = await getCompetitorsByProject(project.id);
      setProjectCompetitors(comps as Competitor[]);
      return result.data.id;
    }
    return null;
  };

  const handleAddRef = (data: {
    competitorId: string;
    version?: string;
    featureCoverage?: string;
    technicalApproach?: string;
    prosAndCons?: { pros: string[]; cons: string[] };
  }) => {
    if (!nodeData) return;
    startTransition(async () => {
      if (editingRef) {
        await updateReference(editingRef.reference.id, project.id, data);
      } else {
        await createReference({
          projectId: project.id,
          nodeId: nodeData.node.id,
          ...data,
        });
      }
      const refs = await getReferencesByNode(project.id, nodeData.node.id);
      setNodeRefs(refs as CompetitorReference[]);
      setEditingRef(null);
    });
  };

  const handleDeleteRef = (refId: string) => {
    if (!confirm("确定删除此竞品参考？")) return;
    startTransition(async () => {
      await deleteReference(refId, project.id);
      if (nodeData) {
        const refs = await getReferencesByNode(project.id, nodeData.node.id);
        setNodeRefs(refs as CompetitorReference[]);
      }
    });
  };

  // ─── Computed ─────────────────────────────────────────

  const breadcrumbPath = selectedId ? buildBreadcrumb(tree, selectedId) : [];

  // Field-level completion per PRD F4 AC9:
  // Per dimension: avg of (filled fields / total fields) across records; 0% if no records
  // Total: avg across all enabled dimensions
  const completionPercent = (() => {
    if (!nodeData || dimensions.length === 0) return 0;
    let dimSum = 0;
    for (const dim of dimensions) {
      const records = nodeData.records.filter((r) => r.record.dimensionTypeId === dim.dimType.id);
      if (records.length === 0) {
        dimSum += 0;
        continue;
      }
      const schema = dim.dimType.fieldSchema;
      const totalFields = schema ? Object.keys(schema).length : 1;
      let recordSum = 0;
      for (const r of records) {
        const content = r.record.content;
        if (totalFields <= 1) {
          // Simple dimension: filled if content has any non-empty value
          recordSum += Object.values(content).some((v) => v !== null && v !== undefined && v !== "")
            ? 1
            : 0;
        } else {
          const filled = Object.keys(schema!).filter((key) => {
            const val = content[key];
            return val !== null && val !== undefined && val !== "";
          }).length;
          recordSum += filled / totalFields;
        }
      }
      dimSum += recordSum / records.length;
    }
    return Math.round((dimSum / dimensions.length) * 100);
  })();
  const filledDimensions = nodeData
    ? dimensions.filter((d) =>
        nodeData.records.some((r) => r.record.dimensionTypeId === d.dimType.id),
      ).length
    : 0;
  const totalDimensions = dimensions.length;

  // ─── Render ─────────────────────────────────────────

  return (
    <div className="bg-background flex h-screen">
      {/* Sidebar */}
      <aside
        className={cn(
          "flex flex-col border-r transition-all duration-300",
          sidebarCollapsed ? "w-0 overflow-hidden" : "w-[280px]",
        )}
      >
        <div className="flex h-14 items-center justify-between border-b px-4">
          <div className="flex min-w-0 items-center gap-2">
            <span className="truncate font-semibold">{project.name}</span>
            <Badge variant="outline" className="shrink-0 text-xs">
              {project.templateType === "product_analysis" ? "产品分析" : project.templateType}
            </Badge>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={() => setSidebarCollapsed(true)}
          >
            <PanelLeftClose className="h-4 w-4" />
          </Button>
        </div>
        <div className="border-b px-3 py-2">
          <Button variant="outline" size="sm" className="w-full justify-start text-sm" asChild>
            <Link href={`/projects/${project.id}/import`}>
              <Upload className="mr-2 h-4 w-4" /> 导入文档
            </Link>
          </Button>
        </div>
        <ScrollArea className="flex-1">
          <div className="px-2">
            <FeatureTree
              data={tree}
              selectedId={selectedId}
              onSelect={handleSelectNode}
              onAddChild={handleAddChild}
              onRename={handleRename}
              onDelete={handleDelete}
              onReorder={handleReorder}
              onMove={handleMove}
            />
          </div>
        </ScrollArea>
        <div className="border-t px-3 py-2">
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground w-full justify-start text-sm"
            asChild
          >
            <Link href={`/projects/${project.id}/settings`}>
              <Settings className="mr-2 h-4 w-4" /> 项目设置
            </Link>
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="flex h-14 items-center justify-between border-b px-6">
          <div className="flex items-center gap-4">
            {sidebarCollapsed && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setSidebarCollapsed(false)}
              >
                <PanelLeft className="h-4 w-4" />
              </Button>
            )}
            <Breadcrumb>
              <BreadcrumbList>
                {breadcrumbPath.map((node, i) => {
                  const isLast = i === breadcrumbPath.length - 1;
                  return (
                    <span key={node.id} className="contents">
                      {i > 0 && (
                        <BreadcrumbSeparator>
                          <ChevronRight className="h-4 w-4" />
                        </BreadcrumbSeparator>
                      )}
                      <BreadcrumbItem>
                        {isLast ? (
                          <BreadcrumbPage>{node.name}</BreadcrumbPage>
                        ) : (
                          <span className="text-muted-foreground">{node.name}</span>
                        )}
                      </BreadcrumbItem>
                    </span>
                  );
                })}
              </BreadcrumbList>
            </Breadcrumb>
          </div>
          {selectedType === "file" && nodeData && (
            <div className="flex items-center gap-3">
              <span className="text-muted-foreground text-sm">
                {filledDimensions}/{totalDimensions} 维度已填写
              </span>
              <div className="flex items-center gap-2">
                <Progress value={completionPercent} className="h-2 w-24" />
                <span className="text-sm font-medium">{completionPercent}%</span>
              </div>
              <Separator orientation="vertical" className="h-5" />
              <Button variant="outline" size="sm" className="gap-1.5" asChild>
                <Link href={`/projects/${project.id}/analysis?nodeId=${selectedId}`}>
                  <ClipboardList className="h-3.5 w-3.5" />
                  需求分析
                </Link>
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => setAddRelationDialog(true)}
              >
                <GitBranch className="h-3.5 w-3.5" />
                添加关联
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={handleExportNode}
                disabled={exporting}
              >
                <Download className="h-3.5 w-3.5" />
                导出 Markdown
              </Button>
              {nodeData && nodeData.versions.length >= 3 && (
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  onClick={handleGenerateSnapshot}
                  disabled={snapshotLoading}
                >
                  {snapshotLoading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5" />
                  )}
                  生成当前快照
                </Button>
              )}
            </div>
          )}
        </header>

        {/* Content */}
        <ScrollArea className="flex-1">
          <div className="mx-auto max-w-4xl space-y-4 p-6">
            {/* Import Success Banner (Aha Moment F11 AC6) */}
            {importBanner && (
              <div className="border-primary/30 bg-primary/5 flex items-center gap-3 rounded-lg border p-4">
                <Sparkles className="text-primary h-5 w-5 shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium">
                    成功导入 {importBanner.count} 个文件到「{importBanner.moduleName}」
                  </p>
                  <p className="text-muted-foreground mt-0.5 text-xs">试试完善这个模块的维度信息</p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="shrink-0 text-xs"
                  onClick={() => setImportBanner(null)}
                >
                  知道了
                </Button>
              </div>
            )}

            {isPending && (
              <div className="text-muted-foreground py-8 text-center text-sm">加载中...</div>
            )}

            {/* Panorama prompt after first dimension saved (AC5) */}
            {showPanoramaPrompt && (
              <div className="flex items-center gap-3 rounded-lg border border-green-300 bg-green-50 p-4">
                <Sparkles className="h-5 w-5 shrink-0 text-green-600" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-green-900">
                    第一个维度已填写！查看项目全景图 →
                  </p>
                </div>
                <Button size="sm" variant="outline" asChild>
                  <Link href={`/projects/${project.id}/overview`}>查看全景图</Link>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="shrink-0 text-xs"
                  onClick={() => setShowPanoramaPrompt(false)}
                >
                  稍后
                </Button>
              </div>
            )}

            {/* File view: Dimension cards */}
            {!isPending && selectedType === "file" && nodeData && (
              <>
                {dimensions.map((dim) => {
                  const matchingRecords = nodeData.records.filter(
                    (r) => r.record.dimensionTypeId === dim.dimType.id,
                  );
                  const hasContent = matchingRecords.length > 0;
                  const DimIcon = dimensionIconMap[dim.dimType.key];
                  // F7 AC4: 该维度关联的问题
                  const dimIssues = nodeIssues.filter((issue) => {
                    const cat = issue.category as IssueCategory;
                    return CATEGORY_DIMENSION_MAP[cat] === dim.dimType.key;
                  });

                  return (
                    <DimensionCard
                      key={dim.dimType.id}
                      title={dim.dimType.name}
                      icon={DimIcon}
                      entryCount={matchingRecords.length}
                      defaultExpanded={hasContent}
                      collapsedSummary={hasContent ? undefined : "未填写"}
                      onAdd={() => handleAddDimension(dim.dimType.id, dim.dimType.name)}
                    >
                      {hasContent ? (
                        <div className="space-y-3">
                          {matchingRecords.map((r) => (
                            <div key={r.record.id} className="group relative">
                              {renderDimensionContent(r.dimType.key, r.record.content)}
                              <div className="absolute top-2 right-2 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-7 text-xs"
                                  onClick={() => handleEditDimension(r.record.id, r.record.content)}
                                >
                                  编辑
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-destructive h-7 text-xs"
                                  onClick={() => handleDeleteDimension(r.record.id)}
                                >
                                  删除
                                </Button>
                              </div>
                            </div>
                          ))}
                          {/* F7 AC4: 维度底部展示关联问题 */}
                          {dimIssues.length > 0 && (
                            <>
                              <Separator className="my-2" />
                              <IssueList
                                issues={dimIssues}
                                onAdd={() => setAddIssueDialog(true)}
                                onDelete={handleDeleteIssue}
                                showAddButton={false}
                              />
                            </>
                          )}
                        </div>
                      ) : (
                        <div className="flex flex-col items-center justify-center py-8 text-center">
                          {DimIcon && (
                            <DimIcon className="text-muted-foreground/40 mb-2 h-10 w-10" />
                          )}
                          <p className="text-muted-foreground text-sm">
                            点击添加，或上传文档自动分析
                          </p>
                        </div>
                      )}
                    </DimensionCard>
                  );
                })}

                {/* F7: 关联问题 section */}
                <Card className="border-border/60 p-5 shadow-sm">
                  <IssueList
                    issues={nodeIssues}
                    onAdd={() => setAddIssueDialog(true)}
                    onDelete={handleDeleteIssue}
                  />
                </Card>

                {/* F7: Add Issue Dialog */}
                <AddIssueDialog
                  open={addIssueDialog}
                  onOpenChange={setAddIssueDialog}
                  onSubmit={handleAddIssue}
                />

                {/* F6: 竞品参考 section */}
                <Card className="border-border/60 p-5 shadow-sm">
                  <CompetitorReferenceList
                    references={nodeRefs}
                    competitors={projectCompetitors}
                    onAdd={() => {
                      setEditingRef(null);
                      setAddRefDialog(true);
                    }}
                    onEdit={(ref) => {
                      setEditingRef(ref);
                      setAddRefDialog(true);
                    }}
                    onDelete={handleDeleteRef}
                  />
                </Card>

                {/* F6: Add/Edit Reference Dialog */}
                <AddReferenceDialog
                  open={addRefDialog}
                  onOpenChange={setAddRefDialog}
                  competitors={projectCompetitors}
                  onCreateCompetitor={handleCreateCompetitorInline}
                  onSubmit={handleAddRef}
                  editingRef={editingRef}
                />

                {/* F14: Related Feed Items */}
                {nodeFeedItems.length > 0 && (
                  <Card className="border-border/60 p-5 shadow-sm">
                    <h3 className="mb-3 text-sm font-medium">相关动态</h3>
                    <FeedList items={nodeFeedItems} compact />
                  </Card>
                )}

                {/* Version Timeline */}
                <VersionTimeline
                  versions={nodeData.versions as unknown as VersionRecord[]}
                  versionMode={project.versionMode as "release" | "continuous"}
                  onCreateVersion={handleCreateVersion}
                />
              </>
            )}

            {/* Folder view: Children overview */}
            {!isPending && selectedType === "folder" && folderChildren && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">
                    {breadcrumbPath[breadcrumbPath.length - 1]?.name}
                  </h2>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1.5"
                      onClick={handleExportModule}
                      disabled={exporting}
                    >
                      <Download className="h-4 w-4" />
                      导出模块
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleAddChild(selectedId, "file")}
                    >
                      <Plus className="mr-1 h-4 w-4" /> 添加功能项
                    </Button>
                  </div>
                </div>
                {folderChildren.length === 0 ? (
                  <Card className="border-2 border-dashed p-8 text-center">
                    <BookOpen className="text-primary/40 mx-auto mb-3 h-12 w-12" />
                    <h3 className="mb-2 text-lg font-semibold">从这里开始</h3>
                    <p className="text-muted-foreground mx-auto mb-4 max-w-md text-sm">
                      这个模块还没有内容。你可以手动添加功能项，或导入已有文档快速填充。
                    </p>
                    <div className="flex items-center justify-center gap-3">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleAddChild(selectedId, "file")}
                      >
                        <Plus className="mr-1 h-4 w-4" /> 添加功能项
                      </Button>
                      <Button size="sm" asChild>
                        <Link href={`/projects/${project.id}/import`}>
                          <Upload className="mr-1 h-4 w-4" /> 导入文档
                        </Link>
                      </Button>
                    </div>
                    <div className="mx-auto mt-6 max-w-sm text-left">
                      <p className="text-muted-foreground mb-2 text-xs font-medium">
                        建议记录步骤：
                      </p>
                      <ol className="text-muted-foreground list-inside list-decimal space-y-1.5 text-xs">
                        <li>添加功能项（如：用户登录、数据导出）</li>
                        <li>为每个功能项填写维度信息</li>
                        <li>逐步完善，构建完整知识图谱</li>
                      </ol>
                    </div>
                  </Card>
                ) : (
                  folderChildren.map((child) => (
                    <div
                      key={child.id}
                      className="hover:border-primary/30 cursor-pointer rounded-lg border p-4 transition-colors"
                      onClick={() => handleSelectNode(child.id, child.type as "folder" | "file")}
                    >
                      <div className="flex items-center gap-3">
                        {child.type === "folder" ? (
                          <Folder className="text-primary h-5 w-5" />
                        ) : (
                          <FileText className="text-muted-foreground h-5 w-5" />
                        )}
                        <span className="font-medium">{child.name}</span>
                        <div className="flex-1" />
                        {child.type === "file" && (
                          <>
                            <span className="text-muted-foreground text-sm">
                              {child.filledDimensions}/{child.totalDimensions} 维度
                            </span>
                            <span
                              className={cn(
                                "h-2.5 w-2.5 rounded-full",
                                getStatusColor(child.completionPercent),
                              )}
                            />
                            <span className="text-sm font-medium">{child.completionPercent}%</span>
                          </>
                        )}
                        {child.type === "folder" && child.childCount !== undefined && (
                          <span className="text-muted-foreground text-sm">
                            {child.childCount} 个功能项
                          </span>
                        )}
                        <ChevronRight className="text-muted-foreground h-4 w-4" />
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* First-project welcome card (AC5) */}
            {!isPending && isEmptyProject && !nodeData && !folderChildren && (
              <Card className="border-2 border-dashed p-8 text-center">
                <Sparkles className="text-primary/40 mx-auto mb-3 h-12 w-12" />
                <h3 className="mb-2 text-lg font-semibold">欢迎来到你的新项目</h3>
                <p className="text-muted-foreground mx-auto mb-4 max-w-md text-sm">
                  这个项目还没有内容。你可以导入已有文档快速开始，或手动添加模块逐步构建知识体系。
                </p>
                <div className="flex items-center justify-center gap-3">
                  <Button size="sm" asChild>
                    <Link href={`/projects/${project.id}/import`}>
                      <Upload className="mr-1 h-4 w-4" /> 导入文档
                    </Link>
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleAddChild(null, "folder")}
                  >
                    <Plus className="mr-1 h-4 w-4" /> 手动添加模块
                  </Button>
                </div>
              </Card>
            )}

            {/* Empty state (non-empty project, no selection) */}
            {!isPending && !isEmptyProject && !nodeData && !folderChildren && (
              <div className="text-muted-foreground py-16 text-center">
                <p>选择左侧树中的节点查看详情</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </main>

      {/* ─── Dialogs ─────────────────────────────────── */}

      {/* Add Node */}
      <Dialog open={addNodeDialog} onOpenChange={setAddNodeDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加{addNodeType === "folder" ? "文件夹" : "功能项"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>名称</Label>
              <Input
                value={addNodeName}
                onChange={(e) => setAddNodeName(e.target.value)}
                placeholder={addNodeType === "folder" ? "输入文件夹名称" : "输入功能项名称"}
                onKeyDown={(e) => e.key === "Enter" && handleConfirmAddNode()}
                autoFocus
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddNodeDialog(false)}>
              取消
            </Button>
            <Button onClick={handleConfirmAddNode} disabled={!addNodeName.trim()}>
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={deleteDialog} onOpenChange={setDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              {deleteDescendantInfo && deleteDescendantInfo.childNodeCount > 0
                ? `此操作将同时删除 ${deleteDescendantInfo.childNodeCount} 个子节点和 ${deleteDescendantInfo.dimensionRecordCount} 条维度记录，且不可撤销。`
                : deleteDescendantInfo
                  ? `此操作将删除 ${deleteDescendantInfo.dimensionRecordCount} 条维度记录，且不可撤销。`
                  : "确定要删除此节点吗？此操作不可撤销。"}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialog(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Dimension Record */}
      <Dialog open={addDimDialog} onOpenChange={setAddDimDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加 {addDimTypeName}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>内容</Label>
              <textarea
                className="bg-background focus-visible:ring-ring flex min-h-[120px] w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:outline-none"
                value={addDimContent}
                onChange={(e) => setAddDimContent(e.target.value)}
                placeholder="输入文字内容，或粘贴 JSON 格式数据"
              />
              <p className="text-muted-foreground text-xs">
                纯文本会自动包装为 {"{ text: '...' }"}
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddDimDialog(false)}>
              取消
            </Button>
            <Button onClick={handleConfirmAddDimension} disabled={!addDimContent.trim()}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dimension Record */}
      <Dialog open={editDimDialog} onOpenChange={setEditDimDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑记录</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>内容</Label>
              <textarea
                className="bg-background focus-visible:ring-ring flex min-h-[120px] w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:outline-none"
                value={editDimContent}
                onChange={(e) => setEditDimContent(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDimDialog(false)}>
              取消
            </Button>
            <Button onClick={handleConfirmEditDimension} disabled={!editDimContent.trim()}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Relation Dialog */}
      <Dialog open={addRelationDialog} onOpenChange={setAddRelationDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加关联</DialogTitle>
            <DialogDescription>为当前功能项创建与其他节点的关联关系</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>关联类型</Label>
              <select
                className="bg-background focus-visible:ring-ring flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:ring-2 focus-visible:outline-none"
                value={relationType}
                onChange={(e) => setRelationType(e.target.value)}
              >
                <option value="depends_on">depends_on (依赖)</option>
                <option value="related_to">related_to (相关)</option>
                <option value="conflicts_with">conflicts_with (冲突)</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>目标节点</Label>
              <select
                className="bg-background focus-visible:ring-ring flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:ring-2 focus-visible:outline-none"
                value={relationTargetId}
                onChange={(e) => setRelationTargetId(e.target.value)}
              >
                <option value="">选择目标节点...</option>
                {(function flattenTree(
                  nodes: TreeNode[],
                  prefix = "",
                ): { id: string; label: string }[] {
                  return nodes.flatMap((n) => [
                    { id: n.id, label: prefix + n.name },
                    ...flattenTree(n.children, prefix + n.name + " / "),
                  ]);
                })(tree)
                  .filter((n) => n.id !== selectedId)
                  .map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.label}
                    </option>
                  ))}
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddRelationDialog(false)}>
              取消
            </Button>
            <Button
              disabled={!relationTargetId || relationSaving}
              onClick={async () => {
                setRelationSaving(true);
                const result = await createRelation({
                  sourceNodeId: selectedId,
                  targetNodeId: relationTargetId,
                  relationType,
                });
                setRelationSaving(false);
                if (result.success) {
                  setAddRelationDialog(false);
                  setRelationTargetId("");
                  setRelationType("depends_on");
                }
              }}
            >
              {relationSaving ? "保存中..." : "创建关联"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* F16: Snapshot Result Dialog */}
      <Dialog open={showSnapshotDialog} onOpenChange={setShowSnapshotDialog}>
        <DialogContent className="max-h-[80vh] max-w-2xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="text-primary h-5 w-5" />
              AI 快照
            </DialogTitle>
          </DialogHeader>
          {snapshotData && <SnapshotResult data={snapshotData} onSave={handleSaveSnapshot} />}
        </DialogContent>
      </Dialog>
    </div>
  );
}
