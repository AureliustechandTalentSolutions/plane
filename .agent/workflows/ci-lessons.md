---
description: CI Lessons Learned — Analyze test failures and capture engineering lessons
---

# CI Lessons Learned Workflow

When a CI pipeline fails or produces unexpected results, follow this structured process to diagnose, resolve, and document the issue.

## Steps

1. **Identify the failure**
   - Check the GitHub Actions run log for the failing job
   - Note the workflow name, job name, step name, and error message
   - Determine if this is a new failure or a regression

2. **Classify the failure**
   - **Flaky Test**: Passes sometimes, fails others (timing, concurrency, external deps)
   - **Environment Issue**: Docker service unavailable, wrong Node/Python version, missing deps
   - **Code Bug**: Actual logic error caught by the test
   - **Infrastructure**: GitHub Actions runner issue, cache corruption, network timeout
   - **Configuration**: Missing env var, wrong settings module, path mismatch

3. **Investigate root cause**
   - Review the test output and stack trace
   - Check if the same test passes locally
   - Compare the CI environment with local (Node version, Python version, OS)
   - Check recent commits that may have introduced the failure

4. **Apply the fix**
   - Fix the code, test, or configuration
   - If flaky: add retry logic, increase timeout, or add `@pytest.mark.flaky`
   - If environment: update the CI workflow or devcontainer
   - Run the fix locally before pushing

5. **Document the lesson**
   - Open `LESSONS_LEARNED.md` in the repository root
   - Add a new entry following the template format
   - Include: date, category, context, problem, root cause, resolution, prevention
   - Commit the updated `LESSONS_LEARNED.md` alongside the fix

6. **Verify the fix**
   - Push the fix and monitor the CI pipeline
   - Confirm the previously failing test now passes
   - Check that no new failures were introduced

## Quick Reference: Common CI Failures

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError` | Missing dependency in `requirements/test.txt` | Add the package |
| `ENOENT` / file not found | Missing build step or wrong working directory | Check `cwd` in workflow |
| Test timeout | Slow query or external API call | Add `pytest-timeout`, mock external calls |
| `Connection refused` | Service container not ready | Check `health-cmd` in workflow |
| `pnpm-lock.yaml` mismatch | Dependencies changed without lockfile update | Run `pnpm install` and commit lockfile |
| Coverage below threshold | Insufficient test coverage for changed code | Write more tests or lower threshold temporarily |
