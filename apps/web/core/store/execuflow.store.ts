/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, computed, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
// types
import type {
  IFocusSession,
  IMicroTask,
  IStreak,
  ExecuFlowService as ExecuFlowServiceType,
} from "@plane/services";
// services
import { ExecuFlowService } from "@plane/services";
// plane web store
import type { CoreRootStore } from "./root.store";

// Type aliases for energy level
export type TEnergyLevel = "low" | "medium" | "high";
export type TSessionType = "pomodoro" | "deep_work" | "body_double" | "free_flow";

export interface IExecuFlowStore {
  // State
  activeSession: IFocusSession | null;
  microTasks: IMicroTask[];
  streakData: IStreak | null;
  energyLevel: TEnergyLevel;
  isLoading: boolean;
  error: string | null;

  // Computed
  completedToday: number;
  incompleteMicroTasks: IMicroTask[];

  // Computed functions
  getMicroTaskById: (taskId: string) => IMicroTask | undefined;
  getStreakByType: (streakType: string) => IStreak | undefined;

  // Actions
  fetchActiveSession: () => Promise<void>;
  startFocusSession: (sessionType: TSessionType) => Promise<IFocusSession>;
  endFocusSession: () => Promise<void>;
  fetchMicroTasks: () => Promise<void>;
  createMicroTask: (data: Partial<IMicroTask>) => Promise<IMicroTask>;
  updateMicroTask: (taskId: string, data: Partial<IMicroTask>) => Promise<IMicroTask>;
  completeMicroTask: (taskId: string) => Promise<IMicroTask>;
  deleteMicroTask: (taskId: string) => Promise<void>;
  fetchStreaks: () => Promise<void>;
  updateEnergyLevel: (level: TEnergyLevel) => void;
  clearError: () => void;
}

export class ExecuFlowStore implements IExecuFlowStore {
  // Observables
  activeSession: IFocusSession | null = null;
  microTasks: IMicroTask[] = [];
  streakData: IStreak | null = null;
  energyLevel: TEnergyLevel = "medium";
  isLoading: boolean = false;
  error: string | null = null;

  // Stores
  routerStore;

  // Services
  private execuFlowService: ExecuFlowServiceType;

  constructor(_rootStore: CoreRootStore) {
    makeObservable(this, {
      // Observables
      activeSession: observable.ref,
      microTasks: observable,
      streakData: observable.ref,
      energyLevel: observable,
      isLoading: observable,
      error: observable,
      // Computed
      completedToday: computed,
      incompleteMicroTasks: computed,
      // Actions
      fetchActiveSession: action,
      startFocusSession: action,
      endFocusSession: action,
      fetchMicroTasks: action,
      createMicroTask: action,
      updateMicroTask: action,
      completeMicroTask: action,
      deleteMicroTask: action,
      fetchStreaks: action,
      updateEnergyLevel: action,
      clearError: action,
    });

    // Router store
    this.routerStore = _rootStore.router;
    // Services
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
    this.execuFlowService = new ExecuFlowService(apiBaseUrl || "http://localhost:8000");
  }

  /**
   * @description Get count of tasks completed today
   * @returns {number}
   */
  get completedToday(): number {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    return this.microTasks.filter((task) => {
      if (!task.is_completed || !task.completed_at) return false;
      const completedDate = new Date(task.completed_at);
      completedDate.setHours(0, 0, 0, 0);
      return completedDate.getTime() === today.getTime();
    }).length;
  }

  /**
   * @description Get incomplete micro tasks
   * @returns {IMicroTask[]}
   */
  get incompleteMicroTasks(): IMicroTask[] {
    return this.microTasks.filter((task) => !task.is_completed);
  }

  /**
   * @description Get micro task by ID
   * @param {string} taskId
   * @returns {IMicroTask | undefined}
   */
  getMicroTaskById = computedFn((taskId: string): IMicroTask | undefined =>
    this.microTasks.find((task) => task.id === taskId)
  );

  /**
   * @description Get streak by type
   * @param {string} streakType
   * @returns {IStreak | undefined}
   */
  getStreakByType = computedFn((streakType: string): IStreak | undefined => {
    // Currently only storing one streak, but this allows for future expansion
    return this.streakData?.streak_type === streakType ? this.streakData : undefined;
  });

  /**
   * @description Fetch active focus session
   * @returns {Promise<void>}
   */
  fetchActiveSession = async (): Promise<void> => {
    const workspaceSlug = this.routerStore.workspaceSlug;
    const projectId = this.routerStore.projectId;

    if (!workspaceSlug || !projectId) {
      throw new Error("Workspace slug and project ID are required");
    }

    try {
      runInAction(() => {
        this.isLoading = true;
        this.error = null;
      });

      const sessions = await this.execuFlowService.listFocusSessions(workspaceSlug, projectId, {
        is_active: "true",
      });

      runInAction(() => {
        this.activeSession = sessions.length > 0 ? sessions[0] : null;
        this.isLoading = false;
      });
    } catch (error) {
      runInAction(() => {
        this.error = error instanceof Error ? error.message : "Failed to fetch active session";
        this.isLoading = false;
      });
      throw error;
    }
  };

  /**
   * @description Start a new focus session
   * @param {TSessionType} sessionType
   * @returns {Promise<IFocusSession>}
   */
  startFocusSession = async (sessionType: TSessionType): Promise<IFocusSession> => {
    const workspaceSlug = this.routerStore.workspaceSlug;
    const projectId = this.routerStore.projectId;

    if (!workspaceSlug || !projectId) {
      throw new Error("Workspace slug and project ID are required");
    }

    try {
      runInAction(() => {
        this.isLoading = true;
        this.error = null;
      });

      const sessionData: Partial<IFocusSession> = {
        session_type: sessionType,
        planned_duration_minutes: sessionType === "pomodoro" ? 25 : 90,
        is_active: true,
      };

      const newSession = await this.execuFlowService.createFocusSession(workspaceSlug, projectId, sessionData);

      runInAction(() => {
        this.activeSession = newSession;
        this.isLoading = false;
      });

      return newSession;
    } catch (error) {
      runInAction(() => {
        this.error = error instanceof Error ? error.message : "Failed to start focus session";
        this.isLoading = false;
      });
      throw error;
    }
  };

  /**
   * @description End the active focus session
   * @returns {Promise<void>}
   */
  endFocusSession = async (): Promise<void> => {
    const workspaceSlug = this.routerStore.workspaceSlug;
    const projectId = this.routerStore.projectId;

    if (!workspaceSlug || !projectId) {
      throw new Error("Workspace slug and project ID are required");
    }

    if (!this.activeSession) {
      throw new Error("No active session");
    }

    try {
      runInAction(() => {
        this.isLoading = true;
        this.error = null;
      });

      await this.execuFlowService.updateFocusSession(workspaceSlug, projectId, this.activeSession.id, {
        is_active: false,
        ended_at: new Date().toISOString(),
      });

      runInAction(() => {
        this.activeSession = null;
        this.isLoading = false;
      });
    } catch (error) {
      runInAction(() => {
        this.error = error instanceof Error ? error.message : "Failed to end focus session";
        this.isLoading = false;
      });
      throw error;
    }
  };

  /**
   * @description Fetch micro tasks
   * @returns {Promise<void>}
   */
  fetchMicroTasks = async (): Promise<void> => {
    const workspaceSlug = this.routerStore.workspaceSlug;
    const projectId = this.routerStore.projectId;

    if (!workspaceSlug || !projectId) {
      throw new Error("Workspace slug and project ID are required");
    }

    try {
      runInAction(() => {
        this.isLoading = true;
        this.error = null;
      });

      const tasks = await this.execuFlowService.listMicroTasks(workspaceSlug, projectId);

      runInAction(() => {
        this.microTasks = tasks;
        this.isLoading = false;
      });
    } catch (error) {
      runInAction(() => {
        this.error = error instanceof Error ? error.message : "Failed to fetch micro tasks";
        this.isLoading = false;
      });
      throw error;
    }
  };

  /**
   * @description Create a new micro task
   * @param {Partial<IMicroTask>} data
   * @returns {Promise<IMicroTask>}
   */
  createMicroTask = async (data: Partial<IMicroTask>): Promise<IMicroTask> => {
    const workspaceSlug = this.routerStore.workspaceSlug;
    const projectId = this.routerStore.projectId;

    if (!workspaceSlug || !projectId) {
      throw new Error("Workspace slug and project ID are required");
    }

    try {
      runInAction(() => {
        this.isLoading = true;
        this.error = null;
      });

      const newTask = await this.execuFlowService.createMicroTask(workspaceSlug, projectId, data);

      runInAction(() => {
        this.microTasks = [...this.microTasks, newTask];
        this.isLoading = false;
      });

      return newTask;
    } catch (error) {
      runInAction(() => {
        this.error = error instanceof Error ? error.message : "Failed to create micro task";
        this.isLoading = false;
      });
      throw error;
    }
  };

  /**
   * @description Update a micro task
   * @param {string} taskId
   * @param {Partial<IMicroTask>} data
   * @returns {Promise<IMicroTask>}
   */
  updateMicroTask = async (taskId: string, data: Partial<IMicroTask>): Promise<IMicroTask> => {
    const workspaceSlug = this.routerStore.workspaceSlug;
    const projectId = this.routerStore.projectId;

    if (!workspaceSlug || !projectId) {
      throw new Error("Workspace slug and project ID are required");
    }

    // Find task index
    const taskIndex = this.microTasks.findIndex((task) => task.id === taskId);
    if (taskIndex === -1) throw new Error("Task not found");

    // Store original for rollback
    const originalTask = { ...this.microTasks[taskIndex] };

    try {
      // Optimistic update
      runInAction(() => {
        this.microTasks[taskIndex] = {
          ...this.microTasks[taskIndex],
          ...data,
        };
        this.error = null;
      });

      const updatedTask = await this.execuFlowService.updateMicroTask(workspaceSlug, projectId, taskId, data);

      runInAction(() => {
        this.microTasks[taskIndex] = updatedTask;
      });

      return updatedTask;
    } catch (error) {
      // Rollback on error
      runInAction(() => {
        this.microTasks[taskIndex] = originalTask;
        this.error = error instanceof Error ? error.message : "Failed to update micro task";
      });
      throw error;
    }
  };

  /**
   * @description Complete a micro task
   * @param {string} taskId
   * @returns {Promise<IMicroTask>}
   */
  completeMicroTask = async (taskId: string): Promise<IMicroTask> =>
    this.updateMicroTask(taskId, {
      is_completed: true,
      completed_at: new Date().toISOString(),
    });

  /**
   * @description Delete a micro task
   * @param {string} taskId
   * @returns {Promise<void>}
   */
  deleteMicroTask = async (taskId: string): Promise<void> => {
    const workspaceSlug = this.routerStore.workspaceSlug;
    const projectId = this.routerStore.projectId;

    if (!workspaceSlug || !projectId) {
      throw new Error("Workspace slug and project ID are required");
    }

    // Store original for rollback
    const originalTasks = [...this.microTasks];

    try {
      // Optimistic delete
      runInAction(() => {
        this.microTasks = this.microTasks.filter((task) => task.id !== taskId);
        this.error = null;
      });

      await this.execuFlowService.deleteMicroTask(workspaceSlug, projectId, taskId);
    } catch (error) {
      // Rollback on error
      runInAction(() => {
        this.microTasks = originalTasks;
        this.error = error instanceof Error ? error.message : "Failed to delete micro task";
      });
      throw error;
    }
  };

  /**
   * @description Fetch streak data
   * @returns {Promise<void>}
   */
  fetchStreaks = async (): Promise<void> => {
    const workspaceSlug = this.routerStore.workspaceSlug;
    const projectId = this.routerStore.projectId;

    if (!workspaceSlug || !projectId) {
      throw new Error("Workspace slug and project ID are required");
    }

    try {
      runInAction(() => {
        this.isLoading = true;
        this.error = null;
      });

      const streaks = await this.execuFlowService.getStreaks(workspaceSlug, projectId);

      runInAction(() => {
        // Store the most relevant streak (e.g., focus_session streak)
        this.streakData = streaks.find((s) => s.streak_type === "focus_session") || streaks[0] || null;
        this.isLoading = false;
      });
    } catch (error) {
      runInAction(() => {
        this.error = error instanceof Error ? error.message : "Failed to fetch streaks";
        this.isLoading = false;
      });
      throw error;
    }
  };

  /**
   * @description Update energy level
   * @param {TEnergyLevel} level
   */
  updateEnergyLevel = (level: TEnergyLevel): void => {
    runInAction(() => {
      this.energyLevel = level;
    });
  };

  /**
   * @description Clear error state
   */
  clearError = (): void => {
    runInAction(() => {
      this.error = null;
    });
  };
}
