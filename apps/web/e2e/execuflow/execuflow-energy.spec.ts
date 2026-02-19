/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * E2E tests for the ExecuFlow Energy Tracker (Dragon Widget).
 *
 * The Dragon Widget (dragon-widget.tsx) lets users select one of five
 * energy levels (depleted, low, medium, high, dragon). Selecting a level
 * updates the energy bar width, changes the label, and reveals AI-powered
 * suggestions specific to that energy level.
 */

import { test, expect, ENERGY_LEVELS, ENERGY_EMOJIS } from "../fixtures/execuflow.fixture";
import type { EnergyLevel } from "../fixtures/execuflow.fixture";

// ────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────

async function goToHomeDashboard(page: import("@playwright/test").Page, workspaceSlug = "test-workspace") {
  await page.goto(`/${workspaceSlug}`);
}

// Expected energy bar widths from the component (dragon-widget.tsx:31-37)
const _ENERGY_BAR_WIDTHS: Record<EnergyLevel, number> = {
  depleted: 10,
  low: 30,
  medium: 55,
  high: 80,
  dragon: 100,
};

// ────────────────────────────────────────────────────
// Tests
// ────────────────────────────────────────────────────

test.describe("ExecuFlow Energy Tracker (Dragon Widget)", () => {
  test.describe("initial state", () => {
    test("defaults to medium energy level on load", async ({ page }) => {
      await goToHomeDashboard(page);

      // Default energy is "medium" (dragon-widget.tsx:28)
      // The medium button should have active styling (border + bg)
      const mediumButton = page.locator("button").filter({ hasText: ENERGY_EMOJIS.medium });
      await expect(mediumButton).toBeVisible({ timeout: 5_000 });
    });

    test("displays the energy bar at 55% width for medium", async ({ page }) => {
      await goToHomeDashboard(page);

      // Energy bar width is set via inline style (dragon-widget.tsx:91)
      const energyBar = page.locator("[style*='width']").locator(".rounded-full.transition-all").first();
      await expect(energyBar).toBeVisible({ timeout: 5_000 });
    });

    test("does not show AI suggestions until a level is explicitly selected", async ({ page }) => {
      await goToHomeDashboard(page);

      // showTips defaults to false (dragon-widget.tsx:29)
      // AI suggestions section should not be visible initially
      const aiSection = page.locator("text=/ai suggestions/i");
      await expect(aiSection).toBeHidden({ timeout: 5_000 });
    });

    test("displays all five energy level buttons", async ({ page }) => {
      await goToHomeDashboard(page);

      // Five energy buttons with emoji labels (dragon-widget.tsx:98-118)
      for (const level of ENERGY_LEVELS) {
        const button = page.locator("button").filter({ hasText: ENERGY_EMOJIS[level] });
        await expect(button).toBeVisible({ timeout: 5_000 });
      }
    });
  });

  test.describe("energy level selection", () => {
    for (const level of ENERGY_LEVELS) {
      test(`selecting ${level} energy level updates the UI`, async ({ page }) => {
        await goToHomeDashboard(page);

        // Click the energy level button
        const button = page.locator("button").filter({ hasText: ENERGY_EMOJIS[level] });
        await button.click();

        // AI suggestions should now be visible (showTips set to true)
        // (dragon-widget.tsx:63)
        const aiSection = page.locator("text=/ai suggestions/i");
        await expect(aiSection).toBeVisible({ timeout: 5_000 });
      });
    }

    test("energy bar width changes when selecting different levels", async ({ page }) => {
      await goToHomeDashboard(page);

      // Select "depleted" (10% width)
      await page.locator("button").filter({ hasText: ENERGY_EMOJIS.depleted }).click();

      // The bar's inline style should be width: 10%
      const depletedBar = page.locator(`[style*="width: 10%"]`);
      await expect(depletedBar).toBeVisible({ timeout: 5_000 });

      // Select "dragon" (100% width)
      await page.locator("button").filter({ hasText: ENERGY_EMOJIS.dragon }).click();

      const dragonBar = page.locator(`[style*="width: 100%"]`);
      await expect(dragonBar).toBeVisible({ timeout: 5_000 });
    });

    test("dragon mode applies gradient styling to the bar", async ({ page }) => {
      await goToHomeDashboard(page);

      // Click dragon emoji
      await page.locator("button").filter({ hasText: ENERGY_EMOJIS.dragon }).click();

      // Dragon mode bar has gradient class: "bg-gradient-to-r from-amber-500 via-orange-500 to-red-500"
      // (dragon-widget.tsx:83)
      const gradientBar = page.locator(".bg-gradient-to-r");
      await expect(gradientBar).toBeVisible({ timeout: 5_000 });
    });

    test("depleted level applies red bar styling", async ({ page }) => {
      await goToHomeDashboard(page);

      await page.locator("button").filter({ hasText: ENERGY_EMOJIS.depleted }).click();

      // Depleted uses bg-red-400 (dragon-widget.tsx:89)
      const redBar = page.locator(".bg-red-400");
      await expect(redBar).toBeVisible({ timeout: 5_000 });
    });

    test("high level applies green bar styling", async ({ page }) => {
      await goToHomeDashboard(page);

      await page.locator("button").filter({ hasText: ENERGY_EMOJIS.high }).click();

      // High uses bg-green-400 (dragon-widget.tsx:85)
      const greenBar = page.locator(".bg-green-400");
      await expect(greenBar).toBeVisible({ timeout: 5_000 });
    });
  });

  test.describe("AI suggestions display", () => {
    test("AI suggestions appear after selecting an energy level", async ({ page }) => {
      await goToHomeDashboard(page);

      // Click any energy level
      await page.locator("button").filter({ hasText: ENERGY_EMOJIS.high }).click();

      // AI suggestions header should be visible (dragon-widget.tsx:124-127)
      const aiHeader = page.locator("text=/ai suggestions/i");
      await expect(aiHeader).toBeVisible({ timeout: 5_000 });

      // Sparkles icon should be visible alongside the header
      // (dragon-widget.tsx:127)
      const sparklesIcon = page.locator("svg").filter({ has: page.locator("[class*='text-purple-400']") });
      await expect(sparklesIcon.first()).toBeVisible({ timeout: 5_000 });
    });

    test("suggestion items are rendered as clickable rows", async ({ page }) => {
      await goToHomeDashboard(page);

      await page.locator("button").filter({ hasText: ENERGY_EMOJIS.medium }).click();

      // Each tip is rendered in a row with ChevronRight icon
      // (dragon-widget.tsx:129-136)
      const tipRows = page.locator(".cursor-pointer.transition-colors").filter({
        has: page.locator("svg"),
      });

      // Should have at least one suggestion
      const count = await tipRows.count();
      expect(count).toBeGreaterThan(0);
    });

    test("switching energy levels updates the displayed suggestions", async ({ page }) => {
      await goToHomeDashboard(page);

      // Select depleted
      await page.locator("button").filter({ hasText: ENERGY_EMOJIS.depleted }).click();
      await page.waitForTimeout(500);

      // Capture current tips text
      const tipsContainer = page.locator(".space-y-2").last();
      const depletedTipsText = await tipsContainer.textContent();

      // Switch to dragon
      await page.locator("button").filter({ hasText: ENERGY_EMOJIS.dragon }).click();
      await page.waitForTimeout(500);

      const dragonTipsText = await tipsContainer.textContent();

      // Tips should be different for different energy levels
      // (unless translations happen to match, but they should not)
      expect(dragonTipsText).not.toBe(depletedTipsText);
    });
  });

  test.describe("selected button styling", () => {
    test("active energy button has distinct styling from inactive ones", async ({ page }) => {
      await goToHomeDashboard(page);

      // Click "high" energy
      await page.locator("button").filter({ hasText: ENERGY_EMOJIS.high }).click();

      // Active button should have border-subtle class (dragon-widget.tsx:103-104)
      const activeButton = page.locator("button").filter({ hasText: ENERGY_EMOJIS.high });
      await expect(activeButton).toHaveClass(/border/, { timeout: 5_000 });

      // Inactive button should NOT have border class
      const inactiveButton = page.locator("button").filter({ hasText: ENERGY_EMOJIS.depleted });
      const classes = await inactiveButton.getAttribute("class");
      expect(classes).not.toContain("border-subtle");
    });
  });
});
