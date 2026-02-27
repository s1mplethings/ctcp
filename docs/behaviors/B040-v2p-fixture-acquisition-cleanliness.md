# B040 v2p fixture acquisition + cleanliness

## Reason
- Make V2P execution deterministic without manual hand-holding by selecting or generating fixtures automatically.
- Prevent cache/runtime artifacts from leaking into pointcloud templates, manifests, and generated project bundles.

## Behavior
- Trigger:
  - `tools/v2p_fixtures.py ensure_fixture(...)` used by `scripts/ctcp_orchestrate.py cos-user-v2p`.
- Inputs / Outputs:
  - Input mode: `auto|synth|path`, repo root, run dir, dialogue callback.
  - Output: resolved fixture selection metadata (`artifacts/fixture_meta.json`) and fixture path for testkit env wiring.
- Invariants:
  - `auto` search order is stable and prioritized by configured roots.
  - `auto` with no candidates prompts exactly one path-or-synth question.
  - `auto` with multiple candidates prompts for deterministic index selection.
  - scaffold manifest excludes cache/runtime paths (`.pytest_cache`, `__pycache__`, `out`, `fixture`, `runs`, etc.).
  - generated template contains `scripts/clean_project.py` and test coverage for safe cleanup scope.

## Result
- Acceptance:
  - `cos-user-v2p --fixture-mode synth` runs without user-provided fixture and emits `artifacts/fixture_meta.json`.
  - fixture discovery unit tests pass.
  - generated pointcloud scaffold excludes cache/runtime artifacts from manifest.
- Evidence:
  - `tools/v2p_fixtures.py`
  - `scripts/ctcp_orchestrate.py`
  - `templates/pointcloud_project/minimal/scripts/clean_project.py`
  - `tests/test_v2p_fixture_discovery.py`
  - `tests/test_cos_user_v2p_runner.py`
- Related Gates: workflow_gate, python_unit_tests, patch_check
