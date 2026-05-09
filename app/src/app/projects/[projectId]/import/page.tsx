import { getProject } from "@/actions/projects";
import { getProjectTree, getProjectDimensions } from "@/actions/nodes";
import { notFound } from "next/navigation";
import { ImportPageClient } from "./import-page-client";

export default async function ImportPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const project = await getProject(projectId);
  if (!project) notFound();

  const tree = await getProjectTree(projectId);
  const dimensions = await getProjectDimensions(projectId);

  // Flatten tree to get all folders for mapping targets
  type FlatFolder = { id: string; name: string; path: string; depth: number };
  function collectFolders(nodes: typeof tree, parentPath: string = ""): FlatFolder[] {
    const result: FlatFolder[] = [];
    for (const n of nodes) {
      if (n.type === "folder") {
        const displayPath = parentPath ? `${parentPath} / ${n.name}` : n.name;
        result.push({ id: n.id, name: n.name, path: displayPath, depth: n.depth });
        if (n.children?.length) {
          result.push(...collectFolders(n.children, displayPath));
        }
      }
    }
    return result;
  }

  const folders = collectFolders(tree);
  const dimOptions = dimensions.map((d) => ({
    id: d.dimType.id,
    key: d.dimType.key,
    name: d.dimType.name,
  }));

  return (
    <ImportPageClient
      projectId={projectId}
      projectName={project.name}
      folders={folders}
      dimensions={dimOptions}
    />
  );
}
