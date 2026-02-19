/**
 * i18n package Vitest configuration
 * SOURCE: feature/nexus-phase2-smart-scaffold packages/i18n/vitest.config.ts
 * Enables unit testing of translation keys and i18n integration
 */

import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    environment: "node",
    globals: true,
    passWithNoTests: true,
    include: ["tests/**/*.test.ts", "tests/**/*.spec.ts"],
    exclude: ["node_modules", "dist"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
});
