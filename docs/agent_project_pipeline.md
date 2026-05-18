# Agent Project Pipeline Mode

`agent-project` is an explicit end-to-end CTCP mode for turning a requirement input into a minimal local deterministic agent project.

It chains these isolated stages:

```text
input requirement
  -> agent manifest
  -> scaffold project
  -> dry-run validation
  -> scaffold tests
  -> pipeline report
```

It is not the default CTCP project-generation flow. Ordinary CTCP project generation still uses `new-run`, `status`, and `advance`.

## Entrypoint

```powershell
.\.venv\Scripts\python.exe scripts\ctcp_orchestrate.py `
  agent-project `
  --input tests\agent_factory_benchmark\fixtures\input_devops_incident.json `
  --output-dir runs\agent_project_devops
```

If `--output-dir` already exists and is not empty, the command fails by default. Use `--force` only when replacing a known output directory. The pipeline refuses dangerous roots such as the repo root, home directory, or drive root.

## Output Shape

```text
runs/agent_project_devops/
  input.json
  manifest.json
  pipeline_report.json
  pipeline_report.md
  scaffold/
    README.md
    manifest.json
    run_agent.py
    sample_input.json
    agents/
    tools/
    workflows/workflow.json
    memory/memory_schema.json
    permissions/permissions.json
    guardrails/guardrails.json
    tests/
      test_manifest_contract.py
      test_permissions.py
      test_workflows.py
      test_dry_run.py
      test_runtime.py
    runtime/
      runtime_engine.py
      runtime_planner.py
      runtime_tools.py
      runtime_permissions.py
      runtime_tool_registry.py
      runtime_tool_executor.py
      runtime_tool_result.py
      runtime_tool_policy.py
      runtime_state.py
      runtime_audit.py
```

`pipeline_report.json` records the real status of each stage. A failing stage is reported as failed; the pipeline does not fabricate dry-run or scaffold-test success.

## Dry Run

The generated scaffold keeps side-effect-free dry-run:

```powershell
python scaffold\run_agent.py --dry-run --input scaffold\sample_input.json
```

Dry-run output is parseable JSON and includes the selected agent, workflow entry state, available tools, blocked tools, pending approvals, and active guardrails. It does not write `runtime_state.json` or `audit/events.jsonl`.

## Minimal Runtime

Real run is:

```powershell
python scaffold\run_agent.py --input scaffold\sample_input.json
```

Real run uses a bounded planner loop before tool execution. The default planner is deterministic: it selects the next action from the user task, manifest tools, workflow context, and observed ToolResult rows. The planner does not decide permissions. Every selected action is normalized through the generated tool registry, checked with the generated policy layer, executed only through exact allowed adapters, audited, and recorded as a ToolResult.

Real run persists `runtime_state.json`, writes `planner_trace.json`, appends `audit/events.jsonl`, advances workflow state, blocks high-risk or unsupported tools, queues approval-required tools as pending approvals, and returns a `final_answer` object.

Planner output includes:

- `planner_mode`
- `planner_trace_path`
- `final_answer.text`
- `final_answer.sources`
- `final_answer.pending_approvals`
- `final_answer.blocked_tools`
- `final_answer.executed_tools`

The loop is bounded by `CTCP_AGENT_MAX_STEPS`, defaulting to `5`. If the planner cannot produce a final answer within the bound, the run fails with `reason=planner_max_steps_exceeded`.

`CTCP_AGENT_PLANNER=provider` is only an interface path unless a provider is separately implemented and configured. In this phase it returns a clear failed result with `reason=provider_planner_unavailable`; it does not call external APIs or fabricate planner success.

No default web access, real external API calls, or real external side-effect tool integrations are added by this mode.

## Explicit Web Tool Capability

Generated projects can include explicit web tools for research-agent manifests. The web tools are not globally available and are not inferred from unknown names.

`web_search` and `fetch_url` execute only when the manifest declares the exact tool name, sets `runtime_adapter` to the matching adapter, marks `side_effect_level=none`, sets `requires_approval=false`, requires audit logging, and lists the selected agent in `allowed_callers`. Otherwise policy returns a blocked ToolResult with `reason=web_permission_denied`.

The only implemented provider is a deterministic test fixture selected with:

```powershell
$env:CTCP_AGENT_WEB_PROVIDER='fixture'
```

The fixture provider reads `tests/fixtures/web_search_fixture.json` or `CTCP_AGENT_WEB_FIXTURE_PATH`. If no provider is configured, web tools fail cleanly with `reason=web_provider_unavailable`, write audit, and return ToolResult JSON. This mode does not claim real internet access.

Web outputs must carry citation data. `web_search` returns `sources`; `fetch_url` returns `source`; runtime output also aggregates `sources`. Missing sources on a web-derived result fail with `reason=missing_sources`. Audit records query strings, fetched URLs, and sources.

## Relationship To Other Modes

- `agent-manifest`: requirement input -> manifest JSON.
- `agent-scaffold`: manifest JSON -> minimal local runtime scaffold.
- `agent-project`: requirement input -> manifest JSON -> runtime scaffold -> dry-run/test report.

All three modes are explicit subcommands and are isolated from ordinary CTCP project generation.

## Current Limits

- The scaffold is not a production agent runtime.
- Tools are contract definitions, not real external integrations.
- The planner is a bounded deterministic selector, not an open-ended LLM agent loop.
- The runtime supports only deterministic local adapters: `classify_input`, `extract_fields`, `summarize_text`, `create_draft`, `write_audit_event`, and `noop_response`.
- Explicit research-agent web manifests may also use fixture-backed `web_search` and `fetch_url`; real internet access is not implemented.
- Every tool decision returns ToolResult fields: `tool_name`, `status`, `reason`, `side_effect_level`, `requires_approval`, `output`, `audit_event_id`, and `duration_ms`.
- Every executed, blocked, pending approval, and unsupported decision writes a `tool_decision` audit event.
- Unknown, external, and near-match tool names are unsupported or blocked; they are not treated as success.
- High-risk tools are blocked or pending approval; approval bypass is not supported.
- Web access is explicit manifest-only and disabled by default.
- The generator and default planner are deterministic and signal-based, not LLM-backed.
- HTTP API serving for generated agent projects is not implemented.
- Benchmarks cover structural, security, semantic, holdout, and e2e pipeline behavior, but they do not prove open-ended planning quality.

## Regression Commands

```powershell
.\.venv\Scripts\python.exe tests\agent_factory_benchmark\run_benchmark.py
.\.venv\Scripts\python.exe tests\agent_runtime_benchmark\run_runtime_benchmark.py
.\.venv\Scripts\python.exe -m unittest tests.test_agent_project_pipeline -v
.\.venv\Scripts\python.exe -m unittest tests.test_agent_project_orchestrator_e2e -v
```
