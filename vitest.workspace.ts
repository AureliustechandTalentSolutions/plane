import { defineWorkspace } from "vitest/config";

export default defineWorkspace([
  // Live server tests (existing)
  "apps/live/vitest.config.ts",
  // Codemods tests (existing)
  "packages/codemods/vitest.config.ts",
  // Web app tests (new)
  "apps/web/vitest.config.ts",
]);
