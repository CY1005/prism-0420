import { getProject } from "@/actions/projects";
import { getProjectTree, getNodeWithDimensions, getProjectDimensions } from "@/actions/nodes";
import { notFound } from "next/navigation";
import { ProjectWorkspace } from "../../workspace";
import type { TreeNode } from "@/components/feature-tree";

export default async function FeatureDetailPage({
  params,
}: {
  params: Promise<{ projectId: string; featureId: string }>;
}) {
  const { projectId, featureId } = await params;
  const project = await getProject(projectId);
  if (!project) notFound();

  const tree = (await getProjectTree(projectId)) as TreeNode[];
  const dimensions = await getProjectDimensions(projectId);

  const nodeData = await getNodeWithDimensions(featureId, projectId);
  if (!nodeData) notFound();

  return (
    <ProjectWorkspace
      project={project}
      tree={tree}
      dimensions={dimensions}
      initialNodeData={nodeData}
      initialSelectedId={featureId}
    />
  );
}
