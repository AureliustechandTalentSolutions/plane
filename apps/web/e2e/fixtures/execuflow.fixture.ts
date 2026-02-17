/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { test as base } from "@playwright/test";
import type { Page, Route } from "@playwright/test";

// ── Constants matching the source components ──

export const FOCUS_DURATIONS = {
  micro: 5 * 60,
  short: 15 * 60,
  flow: 25 * 60,
  deep: 50 * 60,
} as const;

export type SessionType = keyof typeof FOCUS_DURATIONS;

export const ENERGY_LEVELS = ["depleted", "low", "medium", "high", "dragon"] as const;
export type EnergyLevel = (typeof ENERGY_LEVELS)[number];

export const ENERGY_EMOJIS: Record<EnergyLevel, string> = {
  depleted: "\uD83D\uDE34", // sleeping face
  low: "\uD83D\uDD0B", // battery
  medium: "\u26A1", // lightning
  high: "\uD83D\uDE80", // rocket
  dragon: "\uD83D\uDC09", // dragon
};

export const STORAGE_KEYS = {
  ACTIVE_SESSION: "execuflow_active_session",
  COMPLETED_SESSIONS_TODAY: "execuflow_completed_today",
} as const;

// ── API mock helpers ──

interface MockApiOptions {
  workspaceSlug?: string;
  projectId?: string;
}

const DEFAULT_WORKSPACE = "test-workspace";
const DEFAULT_PROJECT = "00000000-0000-0000-0000-000000000001";

/**
 * Builds the ExecuFlow API base path for route interception.
 */
function apiBase(opts: MockApiOptions = {}): string {
  const slug = opts.workspaceSlug ?? DEFAULT_WORKSPACE;
  const pid = opts.projectId ?? DEFAULT_PROJECT;
  return `**/api/v1/workspaces/${slug}/projects/${pid}/execuflow/**`;
}

/**
 * Mock the micro-tasks decompose endpoint to return immediately.
 */
async function mockDecompose(page: Page, opts: MockApiOptions = {}): Promise<void> {
  const slug = opts.workspaceSlug ?? DEFAULT_WORKSPACE;
  const pid = opts.projectId ?? DEFAULT_PROJECT;

  // Intercept POST to decompose endpoint
  await page.route(
    `**/api/v1/workspaces/${slug}/projects/${pid}/execuflow/micro-tasks/decompose/`,
    async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          task_id: "mock-task-001",
          status: "processing",
          message: "Decomposition started",
        }),
      });
    }
  );

  // Intercept task-status polling endpoint
  await page.route(`**/api/v1/workspaces/${slug}/projects/${pid}/execuflow/task-status/*`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        task_id: "mock-task-001",
        status: "SUCCESS",
        result: [
          {
            id: "mt-001",
            title: "Set up project scaffold",
            description_json: {},
            issue: null,
            energy_level: "medium",
            estimated_minutes: 10,
            sort_order: 1,
            is_completed: false,
            completed_at: null,
            just_start_eligible: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          {
            id: "mt-002",
            title: "Write unit tests",
            description_json: {},
            issue: null,
            energy_level: "low",
            estimated_minutes: 15,
            sort_order: 2,
            is_completed: false,
            completed_at: null,
            just_start_eligible: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ],
      }),
    });
  });
}

/**
 * Mock the brain-dump endpoint.
 */
async function mockBrainDump(page: Page, opts: MockApiOptions = {}): Promise<void> {
  const slug = opts.workspaceSlug ?? DEFAULT_WORKSPACE;
  const pid = opts.projectId ?? DEFAULT_PROJECT;

  await page.route(`**/api/v1/workspaces/${slug}/projects/${pid}/execuflow/brain-dump/`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        task_id: "mock-braindump-001",
        status: "processing",
        message: "Brain dump processing started",
      }),
    });
  });

  // Task status for brain dump
  await page.route(`**/api/v1/workspaces/${slug}/projects/${pid}/execuflow/task-status/*`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        task_id: "mock-braindump-001",
        status: "SUCCESS",
        result: {
          raw_text: "Fix the login page, add dark mode, refactor the API service",
          source: "manual",
          extracted_items: [
            { title: "Fix the login page", description: "Login page has UI issues" },
            { title: "Add dark mode", description: "Implement dark mode toggle" },
            { title: "Refactor the API service", description: "Clean up API service layer" },
          ],
          created_issues: [
            { id: "issue-001", name: "Fix the login page" },
            { id: "issue-002", name: "Add dark mode" },
            { id: "issue-003", name: "Refactor the API service" },
          ],
          items_count: 3,
        },
      }),
    });
  });
}

/**
 * Mock all ExecuFlow API endpoints with sensible defaults.
 */
async function mockAllApis(page: Page, opts: MockApiOptions = {}): Promise<void> {
  const slug = opts.workspaceSlug ?? DEFAULT_WORKSPACE;
  const pid = opts.projectId ?? DEFAULT_PROJECT;
  const base = `**/api/v1/workspaces/${slug}/projects/${pid}/execuflow`;

  // Micro tasks list
  await page.route(`${base}/micro-tasks/`, async (route: Route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    } else {
      await route.continue();
    }
  });

  // Focus sessions list
  await page.route(`${base}/focus-sessions/`, async (route: Route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    } else {
      await route.continue();
    }
  });

  // Context snapshots
  await page.route(`${base}/context-snapshots/`, async (route: Route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });

  // Dopamine menu
  await page.route(`${base}/dopamine-menu/`, async (route: Route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });

  // Achievements
  await page.route(`${base}/achievements/`, async (route: Route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });

  // Streaks
  await page.route(`${base}/streaks/`, async (route: Route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
}

// ── localStorage helpers ──

/**
 * Seed a focus session directly into localStorage so the widget
 * renders with a pre-existing session (avoids clicking through UI setup).
 */
async function seedActiveSession(
  page: Page,
  sessionType: SessionType = "flow",
  secondsLeft?: number,
  isPaused = false
): Promise<void> {
  const planned = FOCUS_DURATIONS[sessionType] / 60;
  const secs = secondsLeft ?? FOCUS_DURATIONS[sessionType];

  await page.evaluate(
    ({ key, session }) => {
      localStorage.setItem(key, JSON.stringify(session));
    },
    {
      key: STORAGE_KEYS.ACTIVE_SESSION,
      session: {
        sessionType,
        plannedMinutes: planned,
        startedAt: new Date().toISOString(),
        secondsLeft: secs,
        isPaused,
      },
    }
  );
}

/**
 * Seed the completed session count for today.
 */
async function seedCompletedCount(page: Page, count: number): Promise<void> {
  await page.evaluate(
    ({ key, data }) => {
      localStorage.setItem(key, JSON.stringify(data));
    },
    {
      key: STORAGE_KEYS.COMPLETED_SESSIONS_TODAY,
      data: { count, date: new Date().toDateString() },
    }
  );
}

/**
 * Read the active session from localStorage.
 */
async function getActiveSession(page: Page): Promise<Record<string, unknown> | null> {
  return await page.evaluate((key: string) => {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as Record<string, unknown>) : null;
  }, STORAGE_KEYS.ACTIVE_SESSION);
}

/**
 * Read the completed session count from localStorage.
 */
async function getCompletedCount(page: Page): Promise<number> {
  return await page.evaluate((key: string) => {
    const raw = localStorage.getItem(key);
    if (!raw) return 0;
    const parsed = JSON.parse(raw) as { date: string; count: number };
    return parsed.date === new Date().toDateString() ? parsed.count : 0;
  }, STORAGE_KEYS.COMPLETED_SESSIONS_TODAY);
}

/**
 * Clear all ExecuFlow localStorage keys.
 */
async function clearExecuFlowStorage(page: Page): Promise<void> {
  await page.evaluate((keys: Record<string, string>) => {
    Object.values(keys).forEach((k: string) => localStorage.removeItem(k));
  }, STORAGE_KEYS);
}

// ── Extend Playwright test with ExecuFlow fixtures ──

export interface ExecuFlowFixtures {
  execuflow: {
    seedActiveSession: typeof seedActiveSession;
    seedCompletedCount: typeof seedCompletedCount;
    getActiveSession: typeof getActiveSession;
    getCompletedCount: typeof getCompletedCount;
    clearStorage: typeof clearExecuFlowStorage;
    mockDecompose: typeof mockDecompose;
    mockBrainDump: typeof mockBrainDump;
    mockAllApis: typeof mockAllApis;
    apiBase: typeof apiBase;
  };
}

export const test = base.extend<ExecuFlowFixtures>({
  execuflow: async ({ page }, use) => {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    await use({
      seedActiveSession: (type?, seconds?, paused?) => seedActiveSession(page, type, seconds, paused),
      seedCompletedCount: (count) => seedCompletedCount(page, count),
      getActiveSession: () => getActiveSession(page),
      getCompletedCount: () => getCompletedCount(page),
      clearStorage: () => clearExecuFlowStorage(page),
      mockDecompose: (opts?) => mockDecompose(page, opts),
      mockBrainDump: (opts?) => mockBrainDump(page, opts),
      mockAllApis: (opts?) => mockAllApis(page, opts),
      apiBase,
    });
  },
});

export { expect } from "@playwright/test";
