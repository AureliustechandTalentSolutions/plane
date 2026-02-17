/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
// store
import { useProject } from "@/hooks/store/use-project";

const STORAGE_KEY = "execuflow_default_project";

export interface IUseExecuFlowProject {
  selectedProjectId: string | null;
  setDefaultProject: (projectId: string) => void;
  hasProjects: boolean;
}

/**
 * @description Hook to manage the default project context for ExecuFlow widgets.
 * Persists the selected project ID to localStorage keyed by workspace slug.
 * Falls back to the first joined project if no stored value exists.
 *
 * @param {string} workspaceSlug - The workspace slug used to namespace localStorage
 * @returns {IUseExecuFlowProject}
 */
export function useExecuFlowProject(workspaceSlug: string): IUseExecuFlowProject {
  const { joinedProjectIds } = useProject();

  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    const stored = localStorage.getItem(`${STORAGE_KEY}_${workspaceSlug}`);
    if (stored) return stored;
    return joinedProjectIds.length > 0 ? joinedProjectIds[0] : null;
  });

  const setDefaultProject = (projectId: string): void => {
    localStorage.setItem(`${STORAGE_KEY}_${workspaceSlug}`, projectId);
    setSelectedProjectId(projectId);
  };

  return {
    selectedProjectId,
    setDefaultProject,
    hasProjects: joinedProjectIds.length > 0,
  };
}
