import { ProjectRoleProvider } from "@/contexts/project-role-context";

export default async function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;

  return <ProjectRoleProvider projectId={projectId}>{children}</ProjectRoleProvider>;
}
