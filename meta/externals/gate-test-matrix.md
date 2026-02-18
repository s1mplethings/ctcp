# Externals Review — gate-test-matrix

## Goal
- Build a reproducible gate/regression matrix for workflow checks, contract checks, doc-link sync, assistant tooling, and packaging hygiene.

## Constraints
- Offline only?: No (research online), but execution must be local and repeatable.
- License constraints?: Prefer permissive licenses.
- Must support Windows?: Yes.
- Must be vendorable?: Yes; avoid mandatory new dependencies.

## Candidates
### A) pytest
- Link: https://docs.pytest.org/
- License: MIT
- Activity (last release): 9.0.1 released 2025-09-16.
- Bundle size / deps: Python package.
- Integration plan: use for Python-level assertions in matrix scripts.
- Pros: rich assertion/reporting.
- Cons: adds dependency coupling for infrastructure checks that can run with stdlib.
- Decision: reject as mandatory for this task.

### B) Python `unittest`
- Link: https://docs.python.org/3/library/unittest.html
- License: PSF (Python standard library)
- Activity: maintained with CPython releases.
- Bundle size / deps: zero extra dependencies.
- Integration plan: could host matrix tests as unit suite.
- Pros: no install required.
- Cons: less convenient for mixed shell/fs workflow than a dedicated scenario script.
- Decision: reject as primary runner.

### C) Qt Test
- Link: https://doc.qt.io/qt-6/qttest-index.html
- License: follows Qt licensing for framework usage.
- Activity: maintained with Qt 6 releases.
- Bundle size / deps: requires Qt test harness and built app.
- Integration plan: suitable for GUI interaction assertions (click/drill/zoom/hitbox).
- Pros: native Qt integration.
- Cons: not directly applicable to current headless gate scenarios.
- Decision: defer for GUI-specific phase.

### D) Playwright
- Link: https://playwright.dev/
- License: Apache-2.0
- Activity: actively maintained (v1.55 line in 2025 releases).
- Bundle size / deps: Node stack + browser drivers.
- Integration plan: could validate WebEngine/DOM-like interaction with external harness.
- Pros: strong UI automation.
- Cons: extra toolchain; not needed for immediate gate tests.
- Decision: defer.

## Final pick
- Chosen: repository-native Python scenario runner under `tools/checks/` + existing verify scripts.
- Why:
  - No new runtime dependencies.
  - Can produce deterministic evidence logs for CI/regression.
  - Fits current cross-platform script architecture.
- What code to copy / what API to call:
  - Use `subprocess` + temporary sandbox repo to test gate behavior safely.
  - Emit markdown/json reports for reproducible evidence.

## Evidence
- pytest docs (release): https://docs.pytest.org/en/stable/changelog.html
- unittest docs: https://docs.python.org/3/library/unittest.html
- Qt Test docs: https://doc.qt.io/qt-6/qttest-index.html
- Playwright docs/releases: https://playwright.dev/ and https://github.com/microsoft/playwright/releases
- Accessed on 2026-02-18.
