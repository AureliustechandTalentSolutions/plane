# Lessons Learned — Plane Monorepo

## LL-001: Dev Environment Setup (2026-02-19)

**Category**: Infrastructure  
**Severity**: Medium  
**Root Cause**: Missing `passWithNoTests` in Vitest config caused `pnpm test` to fail when no test files existed  
**Fix**: Added `passWithNoTests: true` to `apps/web/vitest.config.ts` and created starter `smoke.test.ts`  
**Prevention**: Always add `passWithNoTests: true` to new Vitest project configs  

---

## LL-002: Branch Gap Analysis — Config Merge Conflicts (2026-02-19)

**Category**: Architecture / Code Reuse  
**Severity**: High  
**Context**: `feature/nexus-phase2-smart-scaffold` branch (27 commits, 90 files, +18K lines) had 5 conflicting files with the local dev-env setup

### Conflicts Resolved

| File | Resolution | Reuse % |
|------|-----------|---------|
| `vitest.config.ts` | Merged both: our `passWithNoTests` + thresholds + branch's `tsconfigPaths` + Next.js aliases | 80% |
| `vitest.setup.ts` | Took branch's `cleanup()` pattern + our `jest-dom/vitest` import | 90% |
| `apps/web/package.json` | Combined all devDeps: our jsdom@26 + branch's `@vitest/ui`, `@playwright/test` | 85% |
| `requirements/test.txt` | Combined: our `pytest-html/timeout/sugar` + branch's `pytest-asyncio/daphne/channels` | 100% |
| `requirements/base.txt` | Added branch's `channels-redis`, `anthropic`, `google-generativeai` | 95% |

### Key Insights
- **Always check existing `base.txt`** before assuming deps are missing — `channels` was already present, only `channels-redis` was needed
- **Settings files use wildcard imports** (`from .common import *`) — Pylint warnings are expected, not bugs
- **Separate CI workflows > modifying existing** — Our 3-workflow architecture is cleaner than the branch's approach of adding pytest to lint workflows
- **`cleanup()` in vitest.setup.ts is critical** — Prevents React test memory leaks and state bleeding between tests

### V&V Quality Gate: BRAVO TDD Compliance
- All changes follow code reuse protocol (DISCOVERY→ASSESSMENT→ADAPTATION→VALIDATION)
- Coverage thresholds maintained: 50% statements/branches/functions/lines (starter)
- No regressions introduced in existing test suite

---

## LL-003: Template for Future Entries

**Category**: [Infrastructure | Architecture | Testing | CI/CD | Security]  
**Severity**: [Low | Medium | High | Critical]  
**Root Cause**: [description]  
**Fix**: [what was done]  
**Prevention**: [how to prevent recurrence]  
