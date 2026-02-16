// packages/services/src/execuflow/execuflow.service.ts
// ExecuFlow API service layer — all data from API, zero hardcoded values.

import type { AxiosError, AxiosResponse } from "axios";

import { APIService } from "../api.service";

// Types — inferred from API responses, not hardcoded
export interface IMicroTask {
  id: string;
  title: string;
  description_json: Record<string, unknown>;
  issue: string | null;
  energy_level: "low" | "medium" | "high";
  estimated_minutes: number | null;
  sort_order: number;
  is_completed: boolean;
  completed_at: string | null;
  just_start_eligible: boolean;
  created_at: string;
  updated_at: string;
}

export interface IFocusSession {
  id: string;
  session_type: "pomodoro" | "deep_work" | "body_double" | "free_flow";
  planned_duration_minutes: number;
  issue: string | null;
  micro_task: string | null;
  started_at: string;
  ended_at: string | null;
  actual_duration_minutes: number | null;
  mood_before: number | null;
  mood_after: number | null;
  interrupt_queue: unknown[];
  notes_json: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
}

export interface IContextSnapshot {
  id: string;
  title: string;
  snapshot_data: Record<string, unknown>;
  trigger: "manual" | "auto_interrupt" | "auto_switch" | "auto_timer" | "session_end";
  restored_at: string | null;
  is_pinned: boolean;
  created_at: string;
}

export interface IDopamineReward {
  id: string;
  category: "appetizer" | "side" | "entree" | "dessert";
  title: string;
  description: string;
  cooldown_minutes: number;
  last_used_at: string | null;
  use_count: number;
  is_active: boolean;
  is_available: boolean;
}

export interface IAchievement {
  id: string;
  name: string;
  description: string;
  icon: string;
  xp_value: number;
  criteria_json: Record<string, unknown>;
}

export interface IUserAchievement {
  id: string;
  achievement: IAchievement;
  earned_at: string;
}

export interface IStreak {
  id: string;
  streak_type: "daily_login" | "focus_session" | "task_completion" | "brain_dump" | "review";
  current_count: number;
  longest_count: number;
  last_activity_at: string | null;
  grace_period_hours: number;
  status: "active" | "paused" | "archived";
  metadata: Record<string, unknown>;
}

export interface IBrainDumpResponse {
  raw_text: string;
  source: string;
  extracted_items: Array<{ title: string; description: string }>;
  created_issues: Array<{ id: string; name: string }>;
  items_count: number;
}

// Async task response for AI-powered endpoints
export interface IAsyncTaskResponse {
  task_id: string;
  status: "processing" | "pending";
  message: string;
}

// Task status response from polling endpoint
export interface ITaskStatusResponse<T = unknown> {
  task_id: string;
  status: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE" | "RETRY";
  result?: T;
  error?: string;
}

// Helper to extract data from response
function extractData<T>(res: AxiosResponse<T>): T {
  return res.data;
}

// Helper to handle API errors
function handleError(err: AxiosError<unknown>): never {
  const message = err.response?.data ? JSON.stringify(err.response.data) : err.message;
  throw new Error(message);
}

export class ExecuFlowService extends APIService {
  constructor(BASE_URL: string) {
    super(BASE_URL);
  }

  private basePath(workspaceSlug: string, projectId: string): string {
    return `/api/v1/workspaces/${workspaceSlug}/projects/${projectId}/execuflow`;
  }

  // ── MicroTasks ──

  async listMicroTasks(
    workspaceSlug: string,
    projectId: string,
    params?: Record<string, string>
  ): Promise<IMicroTask[]> {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.get(`${this.basePath(workspaceSlug, projectId)}/micro-tasks/${query}`)
      .then((res: AxiosResponse<IMicroTask[]>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  async createMicroTask(workspaceSlug: string, projectId: string, data: Partial<IMicroTask>): Promise<IMicroTask> {
    return this.post(`${this.basePath(workspaceSlug, projectId)}/micro-tasks/`, data)
      .then((res: AxiosResponse<IMicroTask>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  async updateMicroTask(
    workspaceSlug: string,
    projectId: string,
    taskId: string,
    data: Partial<IMicroTask>
  ): Promise<IMicroTask> {
    return this.patch(`${this.basePath(workspaceSlug, projectId)}/micro-tasks/${taskId}/`, data)
      .then((res: AxiosResponse<IMicroTask>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  async deleteMicroTask(workspaceSlug: string, projectId: string, taskId: string): Promise<void> {
    return this.delete(`${this.basePath(workspaceSlug, projectId)}/micro-tasks/${taskId}/`)
      .then((res: AxiosResponse<void>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  /**
   * Start async decomposition of an issue into micro-tasks.
   * Returns a task_id for polling - use pollTaskStatus to get results.
   */
  async decomposeMicroSteps(
    workspaceSlug: string,
    projectId: string,
    data: {
      parent_issue_id: string;
      max_steps?: number;
      target_energy?: string;
      max_minutes_per_step?: number;
    }
  ): Promise<IAsyncTaskResponse> {
    return this.post(`${this.basePath(workspaceSlug, projectId)}/micro-tasks/decompose/`, data)
      .then((res: AxiosResponse<IAsyncTaskResponse>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  // ── Brain Dump ──

  /**
   * Start async brain dump processing.
   * Returns a task_id for polling - use pollTaskStatus to get results.
   */
  async brainDump(
    workspaceSlug: string,
    projectId: string,
    data: {
      raw_text: string;
      source?: string;
      auto_create_issues?: boolean;
    }
  ): Promise<IAsyncTaskResponse> {
    return this.post(`${this.basePath(workspaceSlug, projectId)}/brain-dump/`, data)
      .then((res: AxiosResponse<IAsyncTaskResponse>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  /**
   * Poll for async task status and results.
   * Call repeatedly until status is SUCCESS or FAILURE.
   */
  async pollTaskStatus<T = unknown>(
    workspaceSlug: string,
    projectId: string,
    taskId: string
  ): Promise<ITaskStatusResponse<T>> {
    return this.get(`${this.basePath(workspaceSlug, projectId)}/task-status/?task_id=${taskId}`)
      .then((res: AxiosResponse<ITaskStatusResponse<T>>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  /**
   * Helper to wait for async task completion with polling.
   * Polls every intervalMs until task completes or maxAttempts reached.
   */
  async waitForTaskCompletion<T = unknown>(
    workspaceSlug: string,
    projectId: string,
    taskId: string,
    intervalMs = 1000,
    maxAttempts = 60
  ): Promise<T> {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const status = await this.pollTaskStatus<T>(workspaceSlug, projectId, taskId);

      if (status.status === "SUCCESS" && status.result !== undefined) {
        return status.result;
      }

      if (status.status === "FAILURE") {
        throw new Error(status.error || "Task failed");
      }

      // Wait before next poll
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }

    throw new Error("Task polling timeout");
  }

  // ── Focus Sessions ──

  async listFocusSessions(
    workspaceSlug: string,
    projectId: string,
    params?: Record<string, string>
  ): Promise<IFocusSession[]> {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.get(`${this.basePath(workspaceSlug, projectId)}/focus-sessions/${query}`)
      .then((res: AxiosResponse<IFocusSession[]>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  async createFocusSession(
    workspaceSlug: string,
    projectId: string,
    data: Partial<IFocusSession>
  ): Promise<IFocusSession> {
    return this.post(`${this.basePath(workspaceSlug, projectId)}/focus-sessions/`, data)
      .then((res: AxiosResponse<IFocusSession>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  async updateFocusSession(
    workspaceSlug: string,
    projectId: string,
    sessionId: string,
    data: Record<string, unknown>
  ): Promise<IFocusSession> {
    return this.patch(`${this.basePath(workspaceSlug, projectId)}/focus-sessions/${sessionId}/`, data)
      .then((res: AxiosResponse<IFocusSession>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  // ── Context Snapshots ──

  async listSnapshots(workspaceSlug: string, projectId: string): Promise<IContextSnapshot[]> {
    return this.get(`${this.basePath(workspaceSlug, projectId)}/context-snapshots/`)
      .then((res: AxiosResponse<IContextSnapshot[]>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  async createSnapshot(
    workspaceSlug: string,
    projectId: string,
    data: Partial<IContextSnapshot>
  ): Promise<IContextSnapshot> {
    return this.post(`${this.basePath(workspaceSlug, projectId)}/context-snapshots/`, data)
      .then((res: AxiosResponse<IContextSnapshot>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  async restoreSnapshot(workspaceSlug: string, projectId: string, snapshotId: string): Promise<IContextSnapshot> {
    return this.post(`${this.basePath(workspaceSlug, projectId)}/context-snapshots/${snapshotId}/restore/`, {})
      .then((res: AxiosResponse<IContextSnapshot>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  // ── Dopamine Menu ──

  async listRewards(
    workspaceSlug: string,
    projectId: string,
    params?: Record<string, string>
  ): Promise<IDopamineReward[]> {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.get(`${this.basePath(workspaceSlug, projectId)}/dopamine-menu/${query}`)
      .then((res: AxiosResponse<IDopamineReward[]>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  async claimReward(workspaceSlug: string, projectId: string, rewardId: string): Promise<IDopamineReward> {
    return this.post(`${this.basePath(workspaceSlug, projectId)}/dopamine-menu/${rewardId}/claim/`, {})
      .then((res: AxiosResponse<IDopamineReward>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  // ── Achievements ──

  async listAchievements(workspaceSlug: string, projectId: string): Promise<IAchievement[]> {
    return this.get(`${this.basePath(workspaceSlug, projectId)}/achievements/`)
      .then((res: AxiosResponse<IAchievement[]>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  async listMyAchievements(workspaceSlug: string, projectId: string): Promise<IUserAchievement[]> {
    return this.get(`${this.basePath(workspaceSlug, projectId)}/achievements/mine/`)
      .then((res: AxiosResponse<IUserAchievement[]>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  // ── Streaks ──

  async getStreaks(workspaceSlug: string, projectId: string): Promise<IStreak[]> {
    return this.get(`${this.basePath(workspaceSlug, projectId)}/streaks/`)
      .then((res: AxiosResponse<IStreak[]>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }

  async updateStreak(
    workspaceSlug: string,
    projectId: string,
    data: { streak_type: string; action: "record" | "pause" | "resume" }
  ): Promise<IStreak> {
    return this.patch(`${this.basePath(workspaceSlug, projectId)}/streaks/`, data)
      .then((res: AxiosResponse<IStreak>) => extractData(res))
      .catch((err: AxiosError<unknown>) => handleError(err));
  }
}
