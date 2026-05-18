# Concrete Project Pipeline

The concrete project pipeline is the ordinary CTCP project-generation route:

```text
new-run
-> status
-> advance
-> analysis
-> source_generation
-> project_output
-> generated tests
-> runtime validation
```

This route is separate from the agent runtime line. A concrete project benchmark must not pass by producing an agent manifest, scaffold, runtime loop, or dry-run-only artifact.

## Matrix Coverage

`tests/concrete_project_matrix/run_matrix_benchmark.py` verifies three non-agent project categories:

- `todo_rest_api`
- `markdown_notes_api`
- `simple_auth_api`

`tests/full_stack_app_benchmark/run_full_stack_benchmark.py` verifies small full-stack local app categories:

- `local_task_board_app`
- `local_kanban_board_app`

`tests/non_web_project_matrix/run_non_web_matrix.py` verifies non-web project categories:

- `csv_expense_analyzer`
- `log_analyzer_cli`
- `text_utils_package`
- `terminal_quiz_game`

The benchmark asserts that each run produces a runnable project under `project_output/<project_id>/`, executes generated tests with `python -m unittest discover -v`, exercises the project-specific runtime contract, and verifies persistence/output evidence where applicable. API and full-stack cases start HTTP servers and verify endpoints. Non-web cases run CLI commands, import package functions, or use deterministic terminal-game test mode.

The full-stack benchmark additionally verifies static frontend delivery from `GET /`, `GET /static/app.js`, and `GET /static/styles.css`. The task board case exercises the `/api/tasks` JSON API; the Kanban case exercises boards, cards, card movement, card update/delete, frontend fetch logic, and SQLite board/card persistence.

## Fast Paths

Concrete fast paths are bounded local materializers used only when the user goal matches a supported concrete project category. A local registry dispatches supported categories while shared template and provenance helpers keep generated support files consistent. They preserve the ordinary mainline and record:

```json
{
  "generation_mode": "concrete_fast_path",
  "project_type": "...",
  "provider_authorship": "not_claimed",
  "local_materializer_used": true,
  "repair_attempts": 0
}
```

Fast paths are not mock success. The generated project still has source files, generated tests, startup commands, HTTP runtime validation, and persistence validation.

## Provider-Assisted Mode

`provider_assisted` is an explicit ordinary project-generation mode. It keeps the same route:

```text
new-run -> status -> advance -> analysis -> source_generation -> project_output
```

The deterministic materializer still controls the core project structure, generated tests, persistence guarantees, and runtime validators. Provider participation is bounded to low-risk fragments such as helper functions, documentation notes, formatting helpers, optional frontend helpers, or repair/variation proposals. Fragments must pass syntax, size, and forbidden-token safety checks. Invalid fragments are discarded and the deterministic project output is retained.

Attribution and provenance record the exact provider-assisted evidence:

```json
{
  "generation_mode": "provider_assisted",
  "used_provider_agent": true,
  "provider_authorship": "provider_assisted",
  "provider_assisted_sections": [],
  "provider_generated_files": [],
  "provider_fallbacks": [],
  "provider_validation": {
    "syntax_valid": true,
    "runtime_valid": true,
    "fallback_triggered": false
  }
}
```

The provider-assisted benchmark covers notes, CSV, and Kanban variants and verifies that provider-assisted output differs from deterministic output while runtime behavior remains valid.

## Live Provider-Assisted Smoke Path

`live_provider_assisted` is an explicit smoke mode for ordinary concrete generation. It still follows:

```text
new-run -> status -> advance -> analysis -> source_generation -> project_output
```

Only selected projects can use the live smoke path in this phase:

- `markdown_notes_api`
- `csv_expense_analyzer`
- `local_kanban_board_app`

The live provider can generate only bounded helper, documentation, or optional frontend-helper fragments through `tools/providers/live_provider_adapter.py`. The deterministic materializer continues to own server core, CLI core, database/filesystem persistence, generated tests, and benchmark validators. Provider fragments are restricted to allowlisted paths, size limited, syntax checked, and scanned for subprocess, shell, network, dynamic execution, filesystem traversal, and validation bypass patterns. Invalid output triggers deterministic fallback and records the fallback in attribution.

Live attribution adds:

```json
{
  "generation_mode": "live_provider_assisted",
  "live_provider_used": true,
  "provider_request_count": 1,
  "provider_fragment_count": 1,
  "provider_generated_files": [],
  "provider_fallbacks": [],
  "provider_validation": {
    "syntax_valid": true,
    "runtime_valid": true,
    "fallback_triggered": false
  }
}
```

`tests/live_provider_benchmark/run_live_provider_benchmark.py` verifies real provider calls, fragment generation, generated tests, runtime validation, no agent scaffold substitution, and deterministic fallback safety.

## Live Provider Full Candidate Mode

`live_provider_full_candidate` remains on the ordinary concrete route:

```text
new-run -> status -> advance -> analysis -> source_generation -> project_output
```

Unlike `live_provider_assisted`, the provider may return a complete small project candidate, but only as a structured file manifest for the currently supported small project types:

- `live_provider_text_stats_cli`
- `live_provider_password_policy_package`

The provider cannot write arbitrary paths. CTCP accepts only safe relative paths in the allowed manifest, then runs safety scanning, Python syntax/import validation, generated tests, and project-specific runtime validation. Candidates with forbidden code such as `eval`, `exec`, subprocess, shell, sockets, urllib/requests network code, benchmark edits, or repo verification edits are rejected. Valid candidates can be accepted; limited deterministic repair is recorded; invalid candidates fall back to deterministic materializers.

Attribution adds:

```json
{
  "generation_mode": "live_provider_full_candidate",
  "provider_authorship": "provider_candidate_authored",
  "provider_project_candidate_count": 1,
  "provider_candidate_accepted": true,
  "provider_candidate_repaired": false,
  "fallback_triggered": false,
  "provider_candidate_validation": {
    "manifest_valid": true,
    "paths_safe": true,
    "safety_scan_passed": true,
    "syntax_valid": true,
    "import_valid": true,
    "generated_tests_passed": true,
    "runtime_validation_passed": true
  }
}
```

`tests/live_provider_full_candidate_benchmark/run_live_provider_full_candidate_benchmark.py` validates text-stats CLI generation, password-policy package generation, and invalid-candidate fallback without using agent scaffold artifacts.

## Live Provider Blind Matrix

The blind matrix is the next ordinary concrete-generation check after full-candidate mode. It gives the live provider five small project requests that do not have dedicated deterministic fast paths:

- Unit Converter CLI
- File Renamer Dry-Run CLI
- Mini Markdown Table Formatter
- JSON Config Validator Package
- Simple Static Site Generator

Each case still runs through `new-run -> status -> advance -> analysis -> source_generation -> project_output`. CTCP records `blind_case=true`, `provider_candidate_outcome`, `provider_repair_attempt_count`, `validation_failures`, and fallback evidence in `artifacts/generation_attribution.json`.

The benchmark at `tests/live_provider_blind_matrix/run_live_provider_blind_matrix.py` passes only when every case has attribution, no case is `failed`, generated tests/runtime validators pass for accepted/repaired/fallback cases, and at least three cases are accepted or repaired.

## Attribution

Every ordinary concrete benchmark writes:

```text
artifacts/generation_attribution.json
```

The artifact records the ordinary entrypoint (`new-run/status/advance`), confirms `used_agent_project=false`, `used_agent_scaffold=false`, and `used_local_agent_runtime=false`, and exposes local materializer and provider-authorship evidence. Benchmark reports include an Attribution section so generated projects can be reviewed without inferring whether agent scaffolds or local materializers were involved.

## Runtime Contract

Generated API projects must support:

```powershell
python app.py --host 127.0.0.1 --port <port>
```

The server must remain alive until the benchmark stops it. The benchmark validates project-specific behavior rather than only checking that files exist.

Non-web generated projects do not require a server. They must still provide deterministic local commands or importable package behavior, generated tests, and attribution/provenance artifacts.
