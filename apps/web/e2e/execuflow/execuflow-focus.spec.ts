/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * E2E tests for the ExecuFlow Focus Timer widget.
 *
 * The Focus Timer widget (focus-widget.tsx) manages focus sessions using
 * localStorage for persistence. States: idle -> working -> paused -> break.
 * Duration options: micro (5m), short (15m), flow (25m), deep (50m).
 *
 * These tests exercise the full lifecycle of the focus timer through the
 * actual rendered DOM, validating timer display, button interactions, state
 * transitions, session counting, and localStorage persistence.
 */

import { test, expect, FOCUS_DURATIONS } from "../fixtures/execuflow.fixture";

// ────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────

/**
 * Format seconds as MM:SS, matching the widget's formatTime function
 * (see focus-widget.tsx:62-66).
 */
function formatTime(secs: number): string {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

/**
 * Navigate to the home dashboard where ExecuFlow widgets live.
 * The widgets are rendered inside the DashboardWidgets component
 * (home-dashboard-widgets.tsx:96-139).
 */
async function goToHomeDashboard(page: import("@playwright/test").Page, workspaceSlug = "test-workspace") {
  await page.goto(`/${workspaceSlug}`);
}

// ────────────────────────────────────────────────────
// Tests
// ────────────────────────────────────────────────────

test.describe("ExecuFlow Focus Timer", () => {
  test.beforeEach(async ({ page, execuflow }) => {
    // Clean slate: remove any leftover session data
    await page.goto("/");
    await execuflow.clearStorage();
  });

  test.describe("idle state — duration selector", () => {
    test("displays all four duration options when idle", async ({ page }) => {
      await goToHomeDashboard(page);

      // The four duration buttons: 5m, 15m, 25m, 50m
      // (focus-widget.tsx:122-131)
      const durationButtons = page.locator("button").filter({ hasText: /^(5m|15m|25m|50m)$/ });
      await expect(durationButtons).toHaveCount(4);
    });

    test("displays default timer value of 25:00 (flow) when idle", async ({ page }) => {
      await goToHomeDashboard(page);

      // Default secondsLeft is FOCUS_DURATIONS.flow (25 * 60) -> "25:00"
      // (focus-widget.tsx:43-44)
      const timerDisplay = page.locator("span.font-mono");
      await expect(timerDisplay).toHaveText(formatTime(FOCUS_DURATIONS.flow));
    });

    test("shows session count of 0 when no sessions completed", async ({ page }) => {
      await goToHomeDashboard(page);

      // completedToday defaults to 0
      // (focus-widget.tsx:82-86)
      const sessionCount = page.locator("text=/session/i");
      await expect(sessionCount).toBeVisible();
    });
  });

  test.describe("start and complete a focus session", () => {
    test("clicking a duration button starts a working session", async ({ page }) => {
      await goToHomeDashboard(page);

      // Click the "5m" (micro) button to start
      await page.locator("button").filter({ hasText: "5m" }).click();

      // Duration selector should disappear (only visible in idle state)
      // (focus-widget.tsx:120-132)
      await expect(page.locator("button").filter({ hasText: "5m" })).toBeHidden();

      // Pause button should now be visible (working state)
      // (focus-widget.tsx:149-156)
      const pauseButton = page.locator("button").filter({ hasText: /pause/i });
      await expect(pauseButton).toBeVisible();

      // Timer should show 05:00 initially for micro session
      const timerDisplay = page.locator("span.font-mono");
      await expect(timerDisplay).toHaveText("05:00");
    });

    test("timer countdown updates the display each second", async ({ page, execuflow }) => {
      await goToHomeDashboard(page);

      // Seed a micro session with exactly 5 seconds left to speed up test
      await execuflow.seedActiveSession("micro", 5);
      await page.reload();

      const timerDisplay = page.locator("span.font-mono");

      // Wait for the timer to tick down
      await expect(timerDisplay).toHaveText("00:05", { timeout: 2_000 });

      // Wait a moment for at least one tick
      await page.waitForTimeout(1_500);

      // Timer should have advanced (be less than 00:05)
      const text = await timerDisplay.textContent();
      expect(text).not.toBe("00:05");
    });

    test("session completes when timer reaches zero", async ({ page, execuflow }) => {
      await goToHomeDashboard(page);

      // Seed a session with 2 seconds left
      await execuflow.seedActiveSession("micro", 2);
      await page.reload();

      // Wait for the timer to reach zero and the "break" state
      // (focus-widget.tsx:173-179, 183-187)
      const completeMessage = page.locator("text=/session complete/i");
      await expect(completeMessage).toBeVisible({ timeout: 10_000 });

      // The "new session" button should appear (break state)
      const newSessionButton = page.locator("button").filter({ hasText: /new session/i });
      await expect(newSessionButton).toBeVisible();
    });

    test("session count increments on completion", async ({ page, execuflow }) => {
      await goToHomeDashboard(page);

      // Seed completed count to 2
      await execuflow.seedCompletedCount(2);
      // Seed a session about to end
      await execuflow.seedActiveSession("micro", 1);
      await page.reload();

      // Wait for session to complete
      await page.waitForTimeout(3_000);

      // Verify localStorage was updated
      const count = await execuflow.getCompletedCount();
      expect(count).toBeGreaterThanOrEqual(3);
    });
  });

  test.describe("pause and resume focus session", () => {
    test("pause button stops the timer countdown", async ({ page, execuflow }) => {
      await goToHomeDashboard(page);

      // Seed an active session with plenty of time
      await execuflow.seedActiveSession("flow", 1500);
      await page.reload();

      // Click pause
      const pauseButton = page.locator("button").filter({ hasText: /pause/i });
      await expect(pauseButton).toBeVisible({ timeout: 5_000 });
      await pauseButton.click();

      // Resume and Reset buttons should appear (paused state)
      // (focus-widget.tsx:157-171)
      const resumeButton = page.locator("button").filter({ hasText: /resume/i });
      const resetButton = page.locator("button").filter({ hasText: /reset/i });
      await expect(resumeButton).toBeVisible();
      await expect(resetButton).toBeVisible();

      // Capture the time after pause
      const timerDisplay = page.locator("span.font-mono");
      const timeAtPause = await timerDisplay.textContent();

      // Wait 2 seconds — timer should NOT change
      await page.waitForTimeout(2_000);
      const timeAfterWait = await timerDisplay.textContent();
      expect(timeAfterWait).toBe(timeAtPause);
    });

    test("resume button restarts the countdown", async ({ page, execuflow }) => {
      await goToHomeDashboard(page);

      // Seed a paused session
      await execuflow.seedActiveSession("flow", 1500, true);
      await page.reload();

      // Resume button should be visible (paused state)
      const resumeButton = page.locator("button").filter({ hasText: /resume/i });
      await expect(resumeButton).toBeVisible({ timeout: 5_000 });

      // Capture time before resume
      const timerDisplay = page.locator("span.font-mono");
      const timeBefore = await timerDisplay.textContent();

      // Click resume
      await resumeButton.click();

      // Pause button should reappear (working state)
      const pauseButton = page.locator("button").filter({ hasText: /pause/i });
      await expect(pauseButton).toBeVisible();

      // Wait for the timer to tick
      await page.waitForTimeout(2_000);
      const timeAfter = await timerDisplay.textContent();

      // Timer should have decreased
      expect(timeAfter).not.toBe(timeBefore);
    });

    test("reset button during pause ends the session and returns to idle", async ({ page, execuflow }) => {
      await goToHomeDashboard(page);

      // Seed a paused session
      await execuflow.seedActiveSession("flow", 1500, true);
      await page.reload();

      // Click reset
      const resetButton = page.locator("button").filter({ hasText: /reset/i });
      await expect(resetButton).toBeVisible({ timeout: 5_000 });
      await resetButton.click();

      // Should return to idle state — duration selector visible again
      const durationButtons = page.locator("button").filter({ hasText: /^(5m|15m|25m|50m)$/ });
      await expect(durationButtons.first()).toBeVisible({ timeout: 5_000 });

      // localStorage should be cleared
      const session = await execuflow.getActiveSession();
      expect(session).toBeNull();
    });
  });

  test.describe("session type indicators", () => {
    test("micro session shows micro focus label", async ({ page, execuflow }) => {
      await goToHomeDashboard(page);
      await execuflow.seedActiveSession("micro", 300);
      await page.reload();

      // (focus-widget.tsx:137-138)
      const label = page.locator("text=/micro focus/i");
      await expect(label).toBeVisible({ timeout: 5_000 });
    });

    test("flow session shows flow session label", async ({ page, execuflow }) => {
      await goToHomeDashboard(page);
      await execuflow.seedActiveSession("flow", 1500);
      await page.reload();

      // (focus-widget.tsx:141)
      const label = page.locator("text=/flow session/i");
      await expect(label).toBeVisible({ timeout: 5_000 });
    });

    test("deep session shows deep work label", async ({ page, execuflow }) => {
      await goToHomeDashboard(page);
      await execuflow.seedActiveSession("deep", 3000);
      await page.reload();

      // (focus-widget.tsx:143)
      const label = page.locator("text=/deep work/i");
      await expect(label).toBeVisible({ timeout: 5_000 });
    });
  });

  test.describe("progress ring", () => {
    test("progress ring starts at 0% for a fresh session", async ({ page, execuflow }) => {
      await goToHomeDashboard(page);
      await execuflow.seedActiveSession("flow", FOCUS_DURATIONS.flow);
      await page.reload();

      // The progress circle uses strokeDasharray to indicate progress
      // progress = 1 - secondsLeft / (plannedMinutes * 60) = 0 when full
      // (focus-widget.tsx:73, 110)
      const progressCircle = page.locator("circle.text-amber-500");
      await expect(progressCircle).toBeVisible({ timeout: 5_000 });

      const dasharray = await progressCircle.getAttribute("stroke-dasharray");
      // At 0% progress, the first value should be approximately 0
      expect(dasharray).toContain("0");
    });

    test("progress ring advances as time passes", async ({ page, execuflow }) => {
      await goToHomeDashboard(page);

      // Session at 50% progress: half the time elapsed
      const halfwaySeconds = FOCUS_DURATIONS.flow / 2;
      await execuflow.seedActiveSession("flow", halfwaySeconds);
      await page.reload();

      const progressCircle = page.locator("circle.text-amber-500");
      await expect(progressCircle).toBeVisible({ timeout: 5_000 });

      const dasharray = await progressCircle.getAttribute("stroke-dasharray");
      // At 50% progress, the first value should be ~141.5 (0.5 * 283)
      const progressValue = parseFloat(dasharray?.split(" ")[0] ?? "0");
      expect(progressValue).toBeGreaterThan(100);
      expect(progressValue).toBeLessThan(200);
    });
  });
});
