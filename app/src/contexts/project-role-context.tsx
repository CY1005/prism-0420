"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { getMyProjectRole } from "@/actions/projects";

type ProjectRole = "owner" | "editor" | "viewer" | null;

interface ProjectRoleContextValue {
  role: ProjectRole;
  isViewer: boolean;
  canEdit: boolean;
  canAdmin: boolean;
  loading: boolean;
}

const ProjectRoleContext = createContext<ProjectRoleContextValue>({
  role: null,
  isViewer: false,
  canEdit: false,
  canAdmin: false,
  loading: true,
});

export function ProjectRoleProvider({
  children,
  projectId,
}: {
  children: React.ReactNode;
  projectId: string;
}) {
  const [role, setRole] = useState<ProjectRole>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMyProjectRole(projectId).then((r) => {
      setRole(r);
      setLoading(false);
    });
  }, [projectId]);

  const value: ProjectRoleContextValue = {
    role,
    isViewer: role === "viewer",
    canEdit: role === "owner" || role === "editor",
    canAdmin: role === "owner",
    loading,
  };

  return <ProjectRoleContext.Provider value={value}>{children}</ProjectRoleContext.Provider>;
}

export function useProjectRole() {
  return useContext(ProjectRoleContext);
}
