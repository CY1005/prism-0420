"use client";

import { useState, useEffect } from "react";
import { getProject } from "@/actions/projects";
import { useAuth } from "@/contexts/auth-context";

export function usePageContext(projectId: string) {
  const { user } = useAuth();
  const [projectName, setProjectName] = useState("");

  useEffect(() => {
    getProject(projectId).then((p) => {
      if (p) setProjectName(p.name);
    });
  }, [projectId]);

  const userName = user?.name ?? "";
  const userInitials = user?.name?.charAt(0) ?? "";

  return { projectName, userName, userInitials };
}
