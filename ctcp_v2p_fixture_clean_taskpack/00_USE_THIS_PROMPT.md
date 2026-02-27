# CTCP Task Pack: V2P fixtures auto-acquire + cleanliness hardening

You are a programming agent working on the CTCP repository.
Goal: make the V2P flow usable without hand-holding by:
1) letting the agent automatically obtain a test case (fixture) OR ask the user for one deterministically
2) fixing project/CTCP cleanliness so caches and generated files never pollute templates, manifests, patches, or bundles

This task builds on:
- scaffold-pointcloud (generated project with concrete V2P baseline on .npy fixtures)
- cos-user-v2p (dialogue runner that runs an external testkit and records evidence)

Deliverables MUST pass CTCP `verify_repo.ps1`.

---

## A) Fixture acquisition (auto or user-provided)

### Add to CTCP: fixture selection helper
Add a module: `tools/v2p_fixtures.py` that provides:

- `discover_fixtures(search_roots, max_depth=4) -> list[FixtureCandidate]`
  A fixture candidate is a directory that contains at least:
    - depth.npy
    - poses.npy
    - intrinsics.json
  Optional:
    - sem.npy
    - ref_cloud.ply

- `ensure_fixture(mode, repo, run_dir, user_dialogue) -> FixtureResult`
  Modes:
    - auto (default): try discover in preferred roots; else generate synth
    - synth: generate using <repo>/scripts/make_synth_fixture.py into run_dir/sandbox/fixture/
    - path: require --fixture-path
  For 'auto', search roots in this order:
    1) env `V2P_FIXTURES_ROOT` (if set)
    2) `D:\v2p_fixtures` (Windows)
    3) `<repo>/fixtures` and `<repo>/tests/fixtures`
    4) `<runs_root>/fixtures_cache`
  If none found, ask the user (dialogue) one question:
    - "Provide fixture path, or reply 'synth' to use generated synthetic fixture."

### Wire fixture selection into cos-user-v2p
Add args to `cos-user-v2p`:
- `--fixture-mode auto|synth|path` (default auto)
- `--fixture-path <dir>` (required if mode=path)

Behavior:
- In doc-first `USER_SIM_PLAN.md`, record chosen fixture source and resolved path.
- If mode=auto and discovery finds multiple, ask user to pick one by index (dialogue).
- If synth, generate deterministically (fixed seed) into run_dir/sandbox/fixture.
- Always write `artifacts/fixture_meta.json` into run_dir/artifacts.

---

## B) Cleanliness hardening (no caches / no junk in templates or manifests)

### 1) Template hygiene
Ensure CTCP templates for pointcloud projects NEVER contain runtime artifacts:
- Remove/ignore: `.pytest_cache/`, `__pycache__/`, `*.pyc`, `.DS_Store`, `Thumbs.db`, `.mypy_cache/`, `.ruff_cache/`

### 2) Manifest allowlist
Modify scaffold-pointcloud manifest generation so `meta/manifest.json`:
- lists ONLY scaffold files
- explicitly excludes cache dirs and runtime dirs:
  `.pytest_cache/`, `__pycache__/`, `out/`, `fixture/`, `runs/`

### 3) Generated project .gitignore
Update template `.gitignore` to include:
- `.pytest_cache/`
- `fixture/`
- `out/`
- `runs/`
- `__pycache__/`

### 4) Provide a clean command in generated project
In the generated pointcloud project template add:
- `scripts/clean_project.py`

Deletes only within project root:
- out/, fixture/, runs/
- __pycache__/ and .pytest_cache/ recursively

Add a small test `tests/test_clean_project.py`.

---

## C) Tests / scenarios (CTCP)

1) `tests/test_v2p_fixture_discovery.py`
2) Update `tests/test_cos_user_v2p_runner.py` to run with `--fixture-mode synth` and assert fixture_meta.json exists.

---

## D) Behaviors documentation
Add a behavior doc and register:
- B0xz: v2p fixture acquisition + cleanliness

---

## Acceptance
- CTCP verify_repo passes.
- cos-user-v2p can run with `--fixture-mode synth` without user-provided data.
- auto mode discovers fixtures in unit tests.
- No `.pytest_cache` or `__pycache__` appears in templates or manifest.
- Generated project includes clean_project.py and it works.

Patch-first, minimal unrelated changes.
