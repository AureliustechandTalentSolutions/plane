/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * MERGED: Local dev-env config + feature/nexus-phase2-smart-scaffold
 * - Local: passWithNoTests, coverage thresholds, manual aliases
 * - Branch: tsconfigPaths plugin, Next.js compat aliases
 * Reuse Percentage: 80% (combined best of both)
 */

import { defineConfig } from "vitest/config";
import path from "path";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    passWithNoTests: true,
    setupFiles: ["./vitest.setup.ts"],
    include: [
      "**/__tests__/**/*.{test,spec}.{ts,tsx}",
      "**/*.{test,spec}.{ts,tsx}",
    ],
    exclude: [
      "**/node_modules/**",
      "**/dist/**",
      "**/build/**",
      "**/.react-router/**",
    ],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html", "lcov"],
      include: [
        "app/**/*.{ts,tsx}",
        "core/**/*.{ts,tsx}",
        "ce/**/*.{ts,tsx}",
        "components/**/*.{ts,tsx}",
      ],
      exclude: [
        "**/*.d.ts",
        "**/types.ts",
        "**/types/**",
        "**/__tests__/**",
        "**/*.test.tsx",
        "**/*.test.ts",
        "**/*.spec.tsx",
        "**/*.spec.ts",
        "**/node_modules/**",
      ],
      thresholds: {
        statements: 50,
        branches: 50,
        functions: 50,
        lines: 50,
      },
    },
  },
  plugins: [
    tsconfigPaths({
      projects: [path.resolve(__dirname, "tsconfig.json")],
    }),
  ],
  resolve: {
    alias: {
      // Fallback aliases (tsconfigPaths handles most, these catch edge cases)
      "@": path.resolve(__dirname, "."),
      "@plane/ui": path.resolve(__dirname, "../../packages/ui/src"),
      "@plane/utils": path.resolve(__dirname, "../../packages/utils/src"),
      "@plane/types": path.resolve(__dirname, "../../packages/types/src"),
      "@plane/constants": path.resolve(__dirname, "../../packages/constants/src"),
      // Next.js compat aliases (from branch — needed for migrated components)
      "next/link": path.resolve(__dirname, "app/compat/next/link.tsx"),
      "next/navigation": path.resolve(__dirname, "app/compat/next/navigation.ts"),
      "next/script": path.resolve(__dirname, "app/compat/next/script.tsx"),
    },
  },
});
