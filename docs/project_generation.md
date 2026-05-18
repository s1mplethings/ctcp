# Project Generation

CTCP ordinary project generation uses the `new-run/status/advance` mainline. Agent-specific modes such as `agent-manifest`, `agent-scaffold`, and `agent-project` are explicit isolated commands and are not used to satisfy concrete project generation.

The concrete generation path now includes a generalization matrix for multiple runnable API, full-stack, CLI, package, and terminal-game categories:

- Local Issue Tracker API
- Todo REST API
- Markdown Notes API
- Simple Auth API
- Local Task Board Full-Stack App
- Local Kanban Board Full-Stack App
- CSV Expense Analyzer CLI
- Log Analyzer CLI
- Text Utilities Python Package
- Terminal Quiz Game

Each supported category still goes through analysis and source generation before writing `project_output`. Bounded deterministic materializers may be used for benchmark-stable concrete project categories, but they must be selected through the fast path registry, record provenance, and must not claim provider authorship.

Provider-assisted generation is an explicit generation mode layered on top of the same ordinary mainline. It does not let a provider replace the project structure, persistence contract, generated tests, or runtime validation. Instead, a bounded provider/local fixture can contribute low-risk helper functions, documentation notes, formatting helpers, optional frontend helpers, or repair/variation fragments. Fragments are size-limited, syntax-checked, safety-filtered, and discarded with deterministic fallback when invalid.

Generated projects are validated by real project tests and runtime probes, not by file-existence checks alone. API and full-stack benchmarks start each app with:

```powershell
python app.py --host 127.0.0.1 --port <port>
```

Then it exercises project-specific endpoints and persistence:

- Todo REST API: SQLite-backed CRUD for `/todos`.
- Markdown Notes API: filesystem-backed markdown notes plus `/search?q=`.
- Simple Auth API: SQLite-backed registration, login, token session, protected `/me`, and logout.
- Local Task Board Full-Stack App: static `index.html`/`app.js`/`styles.css` served by the app plus SQLite-backed `/api/tasks` create/list/update/delete.
- Local Kanban Board Full-Stack App: static board frontend, boards/cards JSON API, card move/update/delete flow, and SQLite-backed board/card persistence.
- CSV Expense Analyzer CLI: argparse CLI parses CSV expenses and writes category/monthly totals to JSON.
- Log Analyzer CLI: argparse CLI parses log lines, counts INFO/WARN/ERROR, and writes top error summaries to JSON.
- Text Utilities Python Package: importable package with `slugify`, `word_count`, `extract_keywords`, and `normalize_whitespace`.
- Terminal Quiz Game: CLI game loads JSON questions and supports deterministic `--test-mode` scoring.

Every generated concrete project records provenance at:

```text
artifacts/project_generation_provenance.json
```

The provenance includes the generation mode, project type, local materializer evidence, and bounded repair count.

Each ordinary concrete benchmark also records attribution at:

```text
artifacts/generation_attribution.json
```

Attribution explicitly states that ordinary concrete generation uses `new-run/status/advance`, does not use `agent-project`, `agent-scaffold`, or the local agent runtime, and records whether a local materializer was used. When deterministic materializers produce source files, provider authorship is recorded as `not_claimed`.

When `generation_mode=provider_assisted`, attribution additionally records:

```json
{
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

This mode is provider-assisted under deterministic guardrails, not full autonomous provider-authored generation.

`live_provider_assisted` extends the same contract with a real provider smoke path. It is still not full provider-authored generation: the provider can only return bounded low-risk fragments for selected projects (`markdown_notes_api`, `csv_expense_analyzer`, and `local_kanban_board_app`). The deterministic materializer keeps ownership of core app/server/CLI structure, persistence, generated tests, and runtime validation.

Live provider output is normalized through `tools/providers/live_provider_adapter.py`, restricted to allowlisted fragment paths, size-limited, syntax checked, and scanned for shell, subprocess, network, dynamic execution, file traversal, and validation-bypass tokens. Invalid fragments fall back to deterministic output and attribution records the fallback.

When live mode succeeds, `artifacts/generation_attribution.json` includes:

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

The live provider benchmark is a smoke path only; it proves bounded real-provider participation under deterministic guardrails, not autonomous provider replacement of the project generator.

`live_provider_full_candidate` is the next bounded step. It lets a real provider return a complete small project candidate as a structured file manifest, but only for:

- `live_provider_text_stats_cli`
- `live_provider_password_policy_package`

The ordinary CTCP route is still preserved. Candidate files are extracted only from the provider manifest, written under `project_output/<project_id>/`, and rejected if they use absolute paths, parent traversal, unexpected files, binary-style content, subprocess/shell/network/dynamic-execution tokens, benchmark edits, or repo verification edits. CTCP then runs Python syntax/import checks, generated tests, and project-specific runtime validation. If the candidate is invalid, deterministic fallback materializes a valid project and attribution records the fallback.

When this mode succeeds, `artifacts/generation_attribution.json` includes:

```json
{
  "generation_mode": "live_provider_full_candidate",
  "live_provider_used": true,
  "provider_request_count": 1,
  "provider_project_candidate_count": 1,
  "provider_candidate_accepted": true,
  "provider_candidate_repaired": false,
  "fallback_triggered": false,
  "provider_authorship": "provider_candidate_authored"
}
```

The benchmark at `tests/live_provider_full_candidate_benchmark/run_live_provider_full_candidate_benchmark.py` verifies accepted full candidates for the text-stats CLI and password-policy package, plus an invalid-candidate deterministic fallback case.

## Live Provider Blind Candidate Matrix

`live_provider_blind_candidate` extends full-candidate generation to unseen small project requirements without adding dedicated deterministic fast paths for those blind cases. The current blind matrix covers:

- `live_provider_unit_converter_cli`
- `live_provider_file_renamer_cli`
- `live_provider_markdown_table_formatter`
- `live_provider_json_config_validator`
- `live_provider_static_site_generator`

The provider must still return a structured file manifest. CTCP validates safe relative paths, forbidden-token safety, Python syntax/import behavior, generated tests, and a project-specific runtime validator. A single bounded repair attempt may replace or complete provider candidate files, and every outcome is attributed as `accepted`, `repaired`, `fallback`, `unsupported`, or `failed`.

Blind cases still use ordinary `new-run/status/advance`; they do not use `agent-project`, `agent-scaffold`, or local agent runtime as a substitute. The matrix report is `tests/live_provider_blind_matrix/benchmark_report.md`.
