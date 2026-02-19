import { test, expect } from "@playwright/test";

test.describe("Smoke Tests", () => {
  test("landing page loads successfully", async ({ page }) => {
    const response = await page.goto("/");
    expect(response?.status()).toBeLessThan(400);
  });

  test("page has correct title", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Plane/i);
  });

  test("no console errors on page load", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        errors.push(msg.text());
      }
    });

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Filter out known non-critical errors (e.g., favicon 404)
    const criticalErrors = errors.filter(
      (e) => !e.includes("favicon") && !e.includes("404")
    );

    expect(criticalErrors).toHaveLength(0);
  });

  test("page renders main content area", async ({ page }) => {
    await page.goto("/");
    // Wait for the page to be interactive
    await page.waitForLoadState("domcontentloaded");
    // Verify the body has content
    const body = page.locator("body");
    await expect(body).toBeVisible();
  });
});
