/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * MERGED: Local jest-dom import + branch's cleanup() pattern
 * SOURCE: feature/nexus-phase2-smart-scaffold vitest.setup.ts
 */

import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

// Cleanup after each test to prevent memory leaks and state bleeding
afterEach(() => {
  cleanup();
});
