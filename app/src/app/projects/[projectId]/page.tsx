import { getProject } from "@/actions/projects";
import { getProjectTree, getNodeWithDimensions, getProjectDimensions } from "@/actions/nodes";
import { notFound } from "next/navigation";
import { ProjectWorkspace } from "./workspace";

export default async function ProjectPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const project = await getProject(projectId);
  if (!project) notFound();

  const tree = (await getProjectTree(projectId)) as import("@/components/feature-tree").TreeNode[];
  const dimensions = await getProjectDimensions(projectId);

  // Find the first leaf node to show by default
  function findFirstLeaf(nodes: typeof tree): string | null {
    for (const n of nodes) {
      if (n.type === "file") return n.id;
      if (n.children.length > 0) {
        const found = findFirstLeaf(n.children);
        if (found) return found;
      }
    }
    return null;
  }

  const defaultNodeId = findFirstLeaf(tree);
  const nodeData = defaultNodeId ? await getNodeWithDimensions(defaultNodeId, projectId) : null;

  return (
    <ProjectWorkspace
      project={project}
      tree={tree}
      dimensions={dimensions}
      initialNodeData={nodeData}
      initialSelectedId={defaultNodeId}
    />
  );
}
