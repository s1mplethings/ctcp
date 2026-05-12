# Agent Project Pipeline Mode

`agent-project` is an explicit end-to-end CTCP mode for turning a requirement input into a minimal dry-run agent project.

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
    audit/dry_run_audit.jsonl
```

`pipeline_report.json` records the real status of each stage. A failing stage is reported as failed; the pipeline does not fabricate dry-run or scaffold-test success.

## Dry Run

The generated scaffold is not a full agent runtime. Its `run_agent.py` supports only:

```powershell
python scaffold\run_agent.py --dry-run --input scaffold\sample_input.json
```

Dry-run output is parseable JSON and includes the selected agent, workflow start state, low-risk tools available for dry-run, approval-required actions, active guardrails, and `audit/dry_run_audit.jsonl`.

High-risk tools are never executed. Tools with `requires_approval=true` are listed as pending approval.

## Relationship To Other Modes

- `agent-manifest`: requirement input -> manifest JSON.
- `agent-scaffold`: manifest JSON -> dry-run scaffold.
- `agent-project`: requirement input -> manifest JSON -> dry-run scaffold -> dry-run/test report.

All three modes are explicit subcommands and are isolated from ordinary CTCP project generation.

## Current Limits

- The scaffold is not a production agent runtime.
- Tools are contract definitions, not real external integrations.
- The generator is deterministic and signal-based, not an LLM-backed planner.
- HTTP API serving for generated agent projects is not implemented.
- Benchmarks cover structural, security, semantic, holdout, and e2e pipeline behavior, but they do not prove open-ended planning quality.

## Regression Commands

```powershell
.\.venv\Scripts\python.exe tests\agent_factory_benchmark\run_benchmark.py
.\.venv\Scripts\python.exe -m unittest tests.test_agent_project_pipeline -v
.\.venv\Scripts\python.exe -m unittest tests.test_agent_project_orchestrator_e2e -v
```
