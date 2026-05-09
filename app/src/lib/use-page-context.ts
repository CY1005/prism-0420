"use client";

import { useState, useEffect } from "react";
import { getProject } from "@/actions/projects";
import { getSessionUser } from "@/actions/auth";

export function usePageContext(projectId: string) {
  const [projectName, setProjectName] = useState("");
  const [userName, setUserName] = useState("");
  const [userInitials, setUserInitials] = useState("");

  useEffect(() => {
    getProject(projectId).then((p) => {
      if (p) setProjectName(p.name);
    });
    getSessionUser().then((u) => {
      if (u) {
        setUserName(u.name);
        setUserInitials(u.name.charAt(0));
      }
    });
  }, [projectId]);

  return { projectName, userName, userInitials };
}
