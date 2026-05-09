import { getProject } from "@/actions/projects";
import { getProjectTree, getNodeWithDimensions, getProjectDimensions } from "@/actions/nodes";
import { notFound, redirect } from "next/navigation";
import { ProjectWorkspace } from "../../workspace";
import type { TreeNode } from "@/components/feature-tree";

export default async function ModulePage({
  params,
}: {
  params: Promise<{ projectId: string; moduleId: string }>;
}) {
  const { projectId, moduleId } = await params;
  const project = await getProject(projectId);
  if (!project) notFound();

  const tree = (await getProjectTree(projectId)) as TreeNode[];
  const dimensions = await getProjectDimensions(projectId);

  // Find the moduleId node in the tree
  function findNode(nodes: TreeNode[], id: string): TreeNode | null {
    for (const n of nodes) {
      if (n.id === id) return n;
      if (n.children.length > 0) {
        const found = findNode(n.children, id);
        if (found) return found;
      }
    }
    return null;
  }

  const targetNode = findNode(tree, moduleId);

  // If the node is a file (leaf), redirect to the feature detail page
  if (targetNode && targetNode.type === "file") {
    redirect(`/projects/${projectId}/features/${moduleId}`);
  }

  // For folder view, no initial node data needed
  const nodeData = null;

  return (
    <ProjectWorkspace
      project={project}
      tree={tree}
      dimensions={dimensions}
      initialNodeData={nodeData}
      initialSelectedId={moduleId}
    />
  );
}
