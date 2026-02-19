/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/* eslint-disable @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-return */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { configure } from "mobx";

import type { IFocusSession, IMicroTask, IStreak } from "@plane/services";
import type { TEnergyLevel } from "./execuflow.store";

import { ExecuFlowStore } from "./execuflow.store";
import type { CoreRootStore } from "./root.store";

// Enable strict MobX actions for test fidelity
configure({ enforceActions: "observed" });

// ---------------------------------------------------------------------------
// Mock ExecuFlowService - intercept the module so the store uses our mock
// ---------------------------------------------------------------------------
const mockExecuFlowService = {
  listFocusSessions: vi.fn(),
  createFocusSession: vi.fn(),
  updateFocusSession: vi.fn(),
  listMicroTasks: vi.fn(),
  createMicroTask: vi.fn(),
  updateMicroTask: vi.fn(),
  deleteMicroTask: vi.fn(),
  getStreaks: vi.fn(),
};

vi.mock("@plane/services", () => {
  // Must use a real class so `new ExecuFlowService(...)` works
  const MockClass = vi.fn(function (this: Record<string, unknown>) {
    Object.assign(this, mockExecuFlowService);
  });
  return { ExecuFlowService: MockClass };
});

// ---------------------------------------------------------------------------
// Mock import.meta.env used in the constructor
// ---------------------------------------------------------------------------
vi.stubEnv("VITE_API_BASE_URL", "http://test-api:8000");

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const WORKSPACE_SLUG = "test-workspace";
const PROJECT_ID = "project-123";

function createMockRootStore(overrides?: { workspaceSlug?: string | null; projectId?: string | null }): CoreRootStore {
  return {
    router: {
      workspaceSlug: overrides && "workspaceSlug" in overrides ? overrides.workspaceSlug : WORKSPACE_SLUG,
      projectId: overrides && "projectId" in overrides ? overrides.projectId : PROJECT_ID,
    },
  } as unknown as CoreRootStore;
}

function createMockSession(overrides?: Partial<IFocusSession>): IFocusSession {
  return {
    id: "session-1",
    session_type: "pomodoro",
    planned_duration_minutes: 25,
    issue: null,
    micro_task: null,
    started_at: new Date().toISOString(),
    ended_at: null,
    actual_duration_minutes: null,
    mood_before: null,
    mood_after: null,
    interrupt_queue: [],
    notes_json: {},
    is_active: true,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

function createMockMicroTask(overrides?: Partial<IMicroTask>): IMicroTask {
  return {
    id: "task-1",
    title: "Test micro task",
    description_json: {},
    issue: null,
    energy_level: "medium",
    estimated_minutes: 15,
    sort_order: 0,
    is_completed: false,
    completed_at: null,
    just_start_eligible: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

function createMockStreak(overrides?: Partial<IStreak>): IStreak {
  return {
    id: "streak-1",
    streak_type: "focus_session",
    current_count: 5,
    longest_count: 10,
    last_activity_at: new Date().toISOString(),
    grace_period_hours: 24,
    status: "active",
    metadata: {},
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe("ExecuFlowStore", () => {
  let store: ExecuFlowStore;
  let mockRootStore: CoreRootStore;

  beforeEach(() => {
    vi.clearAllMocks();
    mockRootStore = createMockRootStore();
    store = new ExecuFlowStore(mockRootStore);
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // Initialization
  // ═══════════════════════════════════════════════════════════════════════════
  describe("Initialization", () => {
    it("should initialize with null activeSession", () => {
      expect(store.activeSession).toBeNull();
    });

    it("should initialize with empty microTasks array", () => {
      expect(store.microTasks).toEqual([]);
    });

    it("should initialize with null streakData", () => {
      expect(store.streakData).toBeNull();
    });

    it("should initialize with medium energyLevel", () => {
      expect(store.energyLevel).toBe("medium");
    });

    it("should initialize with isLoading as false", () => {
      expect(store.isLoading).toBe(false);
    });

    it("should initialize with null error", () => {
      expect(store.error).toBeNull();
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // fetchActiveSession
  // ═══════════════════════════════════════════════════════════════════════════
  describe("fetchActiveSession", () => {
    it("should load active session from API and store it", async () => {
      const session = createMockSession();
      mockExecuFlowService.listFocusSessions.mockResolvedValue([session]);

      await store.fetchActiveSession();

      expect(store.activeSession).toEqual(session);
      expect(store.isLoading).toBe(false);
      expect(store.error).toBeNull();
      expect(mockExecuFlowService.listFocusSessions).toHaveBeenCalledWith(WORKSPACE_SLUG, PROJECT_ID, {
        is_active: "true",
      });
    });

    it("should set activeSession to null when no sessions are returned", async () => {
      mockExecuFlowService.listFocusSessions.mockResolvedValue([]);

      await store.fetchActiveSession();

      expect(store.activeSession).toBeNull();
      expect(store.isLoading).toBe(false);
    });

    it("should set isLoading to true while fetching", async () => {
      let loadingDuringFetch = false;
      mockExecuFlowService.listFocusSessions.mockImplementation(() => {
        loadingDuringFetch = store.isLoading;
        return Promise.resolve([]);
      });

      await store.fetchActiveSession();

      expect(loadingDuringFetch).toBe(true);
      expect(store.isLoading).toBe(false);
    });

    it("should set error when API call fails", async () => {
      mockExecuFlowService.listFocusSessions.mockRejectedValue(new Error("Network failure"));

      await expect(store.fetchActiveSession()).rejects.toThrow("Network failure");

      expect(store.error).toBe("Network failure");
      expect(store.isLoading).toBe(false);
    });

    it("should set generic error message for non-Error exceptions", async () => {
      mockExecuFlowService.listFocusSessions.mockRejectedValue("unknown error");

      await expect(store.fetchActiveSession()).rejects.toBe("unknown error");

      expect(store.error).toBe("Failed to fetch active session");
    });

    it("should throw when workspaceSlug is missing", async () => {
      store = new ExecuFlowStore(createMockRootStore({ workspaceSlug: null }));

      await expect(store.fetchActiveSession()).rejects.toThrow("Workspace slug and project ID are required");
    });

    it("should throw when projectId is missing", async () => {
      store = new ExecuFlowStore(createMockRootStore({ projectId: null }));

      await expect(store.fetchActiveSession()).rejects.toThrow("Workspace slug and project ID are required");
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // startFocusSession
  // ═══════════════════════════════════════════════════════════════════════════
  describe("startFocusSession", () => {
    it("should create a session and set it as active", async () => {
      const session = createMockSession({ session_type: "deep_work" });
      mockExecuFlowService.createFocusSession.mockResolvedValue(session);

      const result = await store.startFocusSession("deep_work");

      expect(result).toEqual(session);
      expect(store.activeSession).toEqual(session);
      expect(store.isLoading).toBe(false);
      expect(mockExecuFlowService.createFocusSession).toHaveBeenCalledWith(
        WORKSPACE_SLUG,
        PROJECT_ID,
        expect.objectContaining({
          session_type: "deep_work",
          planned_duration_minutes: 90,
          is_active: true,
        })
      );
    });

    it("should set planned_duration_minutes to 25 for pomodoro", async () => {
      const session = createMockSession({ session_type: "pomodoro", planned_duration_minutes: 25 });
      mockExecuFlowService.createFocusSession.mockResolvedValue(session);

      await store.startFocusSession("pomodoro");

      expect(mockExecuFlowService.createFocusSession).toHaveBeenCalledWith(
        WORKSPACE_SLUG,
        PROJECT_ID,
        expect.objectContaining({
          session_type: "pomodoro",
          planned_duration_minutes: 25,
        })
      );
    });

    it("should set planned_duration_minutes to 90 for non-pomodoro types", async () => {
      const session = createMockSession({ session_type: "body_double" });
      mockExecuFlowService.createFocusSession.mockResolvedValue(session);

      await store.startFocusSession("body_double");

      expect(mockExecuFlowService.createFocusSession).toHaveBeenCalledWith(
        WORKSPACE_SLUG,
        PROJECT_ID,
        expect.objectContaining({
          planned_duration_minutes: 90,
        })
      );
    });

    it("should set error when session creation fails", async () => {
      mockExecuFlowService.createFocusSession.mockRejectedValue(new Error("Create failed"));

      await expect(store.startFocusSession("pomodoro")).rejects.toThrow("Create failed");

      expect(store.error).toBe("Create failed");
      expect(store.isLoading).toBe(false);
    });

    it("should throw when workspace context is missing", async () => {
      store = new ExecuFlowStore(createMockRootStore({ workspaceSlug: null }));

      await expect(store.startFocusSession("pomodoro")).rejects.toThrow("Workspace slug and project ID are required");
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // endFocusSession
  // ═══════════════════════════════════════════════════════════════════════════
  describe("endFocusSession", () => {
    it("should end the active session and clear it", async () => {
      const session = createMockSession();
      store.activeSession = session;
      mockExecuFlowService.updateFocusSession.mockResolvedValue({
        ...session,
        is_active: false,
      });

      await store.endFocusSession();

      expect(store.activeSession).toBeNull();
      expect(store.isLoading).toBe(false);
      expect(mockExecuFlowService.updateFocusSession).toHaveBeenCalledWith(
        WORKSPACE_SLUG,
        PROJECT_ID,
        "session-1",
        expect.objectContaining({
          is_active: false,
          ended_at: expect.any(String),
        })
      );
    });

    it("should throw when no active session exists", async () => {
      await expect(store.endFocusSession()).rejects.toThrow("No active session");
    });

    it("should set error when API call fails", async () => {
      store.activeSession = createMockSession();
      mockExecuFlowService.updateFocusSession.mockRejectedValue(new Error("End failed"));

      await expect(store.endFocusSession()).rejects.toThrow("End failed");

      expect(store.error).toBe("End failed");
      expect(store.isLoading).toBe(false);
    });

    it("should throw when workspace context is missing", async () => {
      store = new ExecuFlowStore(createMockRootStore({ workspaceSlug: null }));
      // Bypass the active session check by setting it directly
      store.activeSession = createMockSession();

      await expect(store.endFocusSession()).rejects.toThrow("Workspace slug and project ID are required");
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // fetchMicroTasks
  // ═══════════════════════════════════════════════════════════════════════════
  describe("fetchMicroTasks", () => {
    it("should fetch and store micro tasks from API", async () => {
      const tasks = [
        createMockMicroTask({ id: "task-1", title: "First" }),
        createMockMicroTask({ id: "task-2", title: "Second" }),
      ];
      mockExecuFlowService.listMicroTasks.mockResolvedValue(tasks);

      await store.fetchMicroTasks();

      expect(store.microTasks).toEqual(tasks);
      expect(store.microTasks).toHaveLength(2);
      expect(store.isLoading).toBe(false);
      expect(mockExecuFlowService.listMicroTasks).toHaveBeenCalledWith(WORKSPACE_SLUG, PROJECT_ID);
    });

    it("should replace existing tasks with fresh data", async () => {
      store.microTasks = [createMockMicroTask({ id: "old-task" })];
      const newTasks = [createMockMicroTask({ id: "new-task" })];
      mockExecuFlowService.listMicroTasks.mockResolvedValue(newTasks);

      await store.fetchMicroTasks();

      expect(store.microTasks).toHaveLength(1);
      expect(store.microTasks[0].id).toBe("new-task");
    });

    it("should set error when fetch fails", async () => {
      mockExecuFlowService.listMicroTasks.mockRejectedValue(new Error("Fetch failed"));

      await expect(store.fetchMicroTasks()).rejects.toThrow("Fetch failed");

      expect(store.error).toBe("Fetch failed");
      expect(store.isLoading).toBe(false);
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // createMicroTask
  // ═══════════════════════════════════════════════════════════════════════════
  describe("createMicroTask", () => {
    it("should create a task and add it to the array", async () => {
      const existingTask = createMockMicroTask({ id: "existing" });
      store.microTasks = [existingTask];

      const newTask = createMockMicroTask({ id: "new-task", title: "New task" });
      mockExecuFlowService.createMicroTask.mockResolvedValue(newTask);

      const result = await store.createMicroTask({ title: "New task" });

      expect(result).toEqual(newTask);
      expect(store.microTasks).toHaveLength(2);
      expect(store.microTasks[1]).toEqual(newTask);
      expect(store.isLoading).toBe(false);
    });

    it("should set error when creation fails", async () => {
      mockExecuFlowService.createMicroTask.mockRejectedValue(new Error("Create failed"));

      await expect(store.createMicroTask({ title: "Test" })).rejects.toThrow("Create failed");

      expect(store.error).toBe("Create failed");
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // updateMicroTask
  // ═══════════════════════════════════════════════════════════════════════════
  describe("updateMicroTask", () => {
    it("should apply optimistic update then confirm with API response", async () => {
      const task = createMockMicroTask({ id: "task-1", title: "Original" });
      store.microTasks = [task];

      const updatedTask = createMockMicroTask({ id: "task-1", title: "Updated from API" });
      let titleDuringApiCall = "";
      mockExecuFlowService.updateMicroTask.mockImplementation(() => {
        // Capture the optimistic state during the API call
        titleDuringApiCall = store.microTasks[0].title;
        return Promise.resolve(updatedTask);
      });

      const result = await store.updateMicroTask("task-1", { title: "Optimistic title" });

      // During the API call, the title should have been optimistically updated
      expect(titleDuringApiCall).toBe("Optimistic title");
      // After API resolves, the task should reflect the server response
      expect(result).toEqual(updatedTask);
      expect(store.microTasks[0].title).toBe("Updated from API");
    });

    it("should roll back on API error", async () => {
      const originalTask = createMockMicroTask({ id: "task-1", title: "Original" });
      store.microTasks = [originalTask];
      mockExecuFlowService.updateMicroTask.mockRejectedValue(new Error("Update failed"));

      await expect(store.updateMicroTask("task-1", { title: "Optimistic" })).rejects.toThrow("Update failed");

      // Should roll back to the original title
      expect(store.microTasks[0].title).toBe("Original");
      expect(store.error).toBe("Update failed");
    });

    it("should throw when task is not found", async () => {
      store.microTasks = [];

      await expect(store.updateMicroTask("nonexistent", { title: "No task" })).rejects.toThrow("Task not found");
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // completeMicroTask
  // ═══════════════════════════════════════════════════════════════════════════
  describe("completeMicroTask", () => {
    it("should set is_completed to true via updateMicroTask", async () => {
      const task = createMockMicroTask({ id: "task-1", is_completed: false });
      store.microTasks = [task];

      const completedTask = createMockMicroTask({
        id: "task-1",
        is_completed: true,
        completed_at: new Date().toISOString(),
      });
      mockExecuFlowService.updateMicroTask.mockResolvedValue(completedTask);

      const result = await store.completeMicroTask("task-1");

      expect(result.is_completed).toBe(true);
      expect(result.completed_at).toBeDefined();
      expect(mockExecuFlowService.updateMicroTask).toHaveBeenCalledWith(
        WORKSPACE_SLUG,
        PROJECT_ID,
        "task-1",
        expect.objectContaining({
          is_completed: true,
          completed_at: expect.any(String),
        })
      );
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // deleteMicroTask
  // ═══════════════════════════════════════════════════════════════════════════
  describe("deleteMicroTask", () => {
    it("should optimistically remove task from the array", async () => {
      const task1 = createMockMicroTask({ id: "task-1" });
      const task2 = createMockMicroTask({ id: "task-2" });
      store.microTasks = [task1, task2];

      let tasksCountDuringApiCall = 0;
      mockExecuFlowService.deleteMicroTask.mockImplementation(() => {
        tasksCountDuringApiCall = store.microTasks.length;
        return Promise.resolve();
      });

      await store.deleteMicroTask("task-1");

      // During API call, task was already removed optimistically
      expect(tasksCountDuringApiCall).toBe(1);
      expect(store.microTasks).toHaveLength(1);
      expect(store.microTasks[0].id).toBe("task-2");
    });

    it("should roll back on API error", async () => {
      const task = createMockMicroTask({ id: "task-1" });
      store.microTasks = [task];
      mockExecuFlowService.deleteMicroTask.mockRejectedValue(new Error("Delete failed"));

      await expect(store.deleteMicroTask("task-1")).rejects.toThrow("Delete failed");

      // Should have restored the original tasks
      expect(store.microTasks).toHaveLength(1);
      expect(store.microTasks[0].id).toBe("task-1");
      expect(store.error).toBe("Delete failed");
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // fetchStreaks
  // ═══════════════════════════════════════════════════════════════════════════
  describe("fetchStreaks", () => {
    it("should fetch streaks and store the focus_session streak", async () => {
      const focusStreak = createMockStreak({ streak_type: "focus_session" });
      const loginStreak = createMockStreak({ id: "streak-2", streak_type: "daily_login" });
      mockExecuFlowService.getStreaks.mockResolvedValue([loginStreak, focusStreak]);

      await store.fetchStreaks();

      expect(store.streakData).toEqual(focusStreak);
      expect(store.isLoading).toBe(false);
    });

    it("should use first streak when no focus_session streak exists", async () => {
      const loginStreak = createMockStreak({ streak_type: "daily_login" });
      mockExecuFlowService.getStreaks.mockResolvedValue([loginStreak]);

      await store.fetchStreaks();

      expect(store.streakData).toEqual(loginStreak);
    });

    it("should set streakData to null when no streaks are returned", async () => {
      mockExecuFlowService.getStreaks.mockResolvedValue([]);

      await store.fetchStreaks();

      expect(store.streakData).toBeNull();
    });

    it("should set error when fetch fails", async () => {
      mockExecuFlowService.getStreaks.mockRejectedValue(new Error("Streak fetch failed"));

      await expect(store.fetchStreaks()).rejects.toThrow("Streak fetch failed");

      expect(store.error).toBe("Streak fetch failed");
      expect(store.isLoading).toBe(false);
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // Computed: completedToday
  // ═══════════════════════════════════════════════════════════════════════════
  describe("computed: completedToday", () => {
    it("should count tasks completed today", () => {
      const todayISO = new Date().toISOString();
      store.microTasks = [
        createMockMicroTask({ id: "t1", is_completed: true, completed_at: todayISO }),
        createMockMicroTask({ id: "t2", is_completed: true, completed_at: todayISO }),
        createMockMicroTask({ id: "t3", is_completed: false, completed_at: null }),
      ];

      expect(store.completedToday).toBe(2);
    });

    it("should not count tasks completed on other days", () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);

      store.microTasks = [
        createMockMicroTask({
          id: "t1",
          is_completed: true,
          completed_at: yesterday.toISOString(),
        }),
        createMockMicroTask({
          id: "t2",
          is_completed: true,
          completed_at: new Date().toISOString(),
        }),
      ];

      expect(store.completedToday).toBe(1);
    });

    it("should return 0 when no tasks are completed", () => {
      store.microTasks = [createMockMicroTask({ id: "t1", is_completed: false })];

      expect(store.completedToday).toBe(0);
    });

    it("should return 0 for empty tasks array", () => {
      expect(store.completedToday).toBe(0);
    });

    it("should not count tasks with is_completed true but null completed_at", () => {
      store.microTasks = [createMockMicroTask({ id: "t1", is_completed: true, completed_at: null })];

      expect(store.completedToday).toBe(0);
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // Computed: incompleteMicroTasks
  // ═══════════════════════════════════════════════════════════════════════════
  describe("computed: incompleteMicroTasks", () => {
    it("should return only incomplete tasks", () => {
      store.microTasks = [
        createMockMicroTask({ id: "t1", is_completed: false }),
        createMockMicroTask({ id: "t2", is_completed: true }),
        createMockMicroTask({ id: "t3", is_completed: false }),
      ];

      const incomplete = store.incompleteMicroTasks;

      expect(incomplete).toHaveLength(2);
      expect(incomplete.map((t) => t.id)).toEqual(["t1", "t3"]);
    });

    it("should return empty array when all tasks are completed", () => {
      store.microTasks = [createMockMicroTask({ id: "t1", is_completed: true })];

      expect(store.incompleteMicroTasks).toHaveLength(0);
    });

    it("should return empty array when no tasks exist", () => {
      expect(store.incompleteMicroTasks).toEqual([]);
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // Computed function: getMicroTaskById
  // ═══════════════════════════════════════════════════════════════════════════
  describe("getMicroTaskById", () => {
    it("should return the task matching the given id", () => {
      const target = createMockMicroTask({ id: "target-id", title: "Target" });
      store.microTasks = [createMockMicroTask({ id: "other-id" }), target];

      expect(store.getMicroTaskById("target-id")).toEqual(target);
    });

    it("should return undefined when task is not found", () => {
      store.microTasks = [createMockMicroTask({ id: "existing" })];

      expect(store.getMicroTaskById("nonexistent")).toBeUndefined();
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // Computed function: getStreakByType
  // ═══════════════════════════════════════════════════════════════════════════
  describe("getStreakByType", () => {
    it("should return streakData when type matches", () => {
      const streak = createMockStreak({ streak_type: "focus_session" });
      store.streakData = streak;

      expect(store.getStreakByType("focus_session")).toEqual(streak);
    });

    it("should return undefined when type does not match", () => {
      store.streakData = createMockStreak({ streak_type: "focus_session" });

      expect(store.getStreakByType("daily_login")).toBeUndefined();
    });

    it("should return undefined when streakData is null", () => {
      store.streakData = null;

      expect(store.getStreakByType("focus_session")).toBeUndefined();
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // updateEnergyLevel
  // ═══════════════════════════════════════════════════════════════════════════
  describe("updateEnergyLevel", () => {
    it("should update energy level to the specified value", () => {
      expect(store.energyLevel).toBe("medium");

      store.updateEnergyLevel("high");
      expect(store.energyLevel).toBe("high");

      store.updateEnergyLevel("low");
      expect(store.energyLevel).toBe("low");
    });

    it.each<TEnergyLevel>(["low", "medium", "high"])("should accept energy level '%s'", (level) => {
      store.updateEnergyLevel(level);
      expect(store.energyLevel).toBe(level);
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // clearError
  // ═══════════════════════════════════════════════════════════════════════════
  describe("clearError", () => {
    it("should reset error to null", () => {
      // Manually set an error via a failed action
      store.error = "Some error";

      store.clearError();

      expect(store.error).toBeNull();
    });

    it("should be safe to call when error is already null", () => {
      expect(store.error).toBeNull();

      store.clearError();

      expect(store.error).toBeNull();
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // Error handling (cross-cutting)
  // ═══════════════════════════════════════════════════════════════════════════
  describe("Error handling", () => {
    it("should clear error on subsequent successful API calls", async () => {
      // First call fails
      mockExecuFlowService.listMicroTasks.mockRejectedValueOnce(new Error("Failed"));
      await expect(store.fetchMicroTasks()).rejects.toThrow();
      expect(store.error).toBe("Failed");

      // Second call succeeds
      mockExecuFlowService.listMicroTasks.mockResolvedValue([]);
      await store.fetchMicroTasks();

      expect(store.error).toBeNull();
    });

    it("should clear previous error at start of each action", async () => {
      store.error = "Previous error";

      mockExecuFlowService.listFocusSessions.mockResolvedValue([]);
      await store.fetchActiveSession();

      expect(store.error).toBeNull();
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // Loading state transitions
  // ═══════════════════════════════════════════════════════════════════════════
  describe("Loading state transitions", () => {
    const asyncActions = [
      {
        name: "fetchActiveSession",
        setup: () => mockExecuFlowService.listFocusSessions.mockResolvedValue([]),
        act: (s: ExecuFlowStore) => s.fetchActiveSession(),
      },
      {
        name: "startFocusSession",
        setup: () => mockExecuFlowService.createFocusSession.mockResolvedValue(createMockSession()),
        act: (s: ExecuFlowStore) => s.startFocusSession("pomodoro"),
      },
      {
        name: "fetchMicroTasks",
        setup: () => mockExecuFlowService.listMicroTasks.mockResolvedValue([]),
        act: (s: ExecuFlowStore) => s.fetchMicroTasks(),
      },
      {
        name: "createMicroTask",
        setup: () => mockExecuFlowService.createMicroTask.mockResolvedValue(createMockMicroTask()),
        act: (s: ExecuFlowStore) => s.createMicroTask({ title: "Test" }),
      },
      {
        name: "fetchStreaks",
        setup: () => mockExecuFlowService.getStreaks.mockResolvedValue([]),
        act: (s: ExecuFlowStore) => s.fetchStreaks(),
      },
    ];

    it.each(asyncActions)("$name should set isLoading=true then false on success", async ({ setup, act }) => {
      setup();
      expect(store.isLoading).toBe(false);

      await act(store);

      expect(store.isLoading).toBe(false);
    });
  });
});
