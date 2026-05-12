# Agent Manifest Mode

`agent-manifest` mode is an explicit CTCP generation mode for producing machine-readable agent manifests from JSON or natural-language requirements.

It is not the default CTCP project-generation flow. Ordinary CTCP project generation still starts with `new-run`, progresses through the artifact-driven orchestrator, and produces runnable MVP project artifacts.

## Entrypoints

Independent generator entrypoint:

```powershell
.\.venv\Scripts\python.exe scripts\generate_agent_manifest.py `
  --input tests\agent_factory_benchmark\fixtures\input_devops_incident.json `
  --output out\agent_manifest.json
```

Explicit orchestrator mode:

```powershell
.\.venv\Scripts\python.exe scripts\ctcp_orchestrate.py `
  agent-manifest `
  --input tests\agent_factory_benchmark\fixtures\input_devops_incident.json `
  --output out\agent_manifest.json
```

Omitting the `agent-manifest` subcommand does not invoke agent manifest generation. This is intentional isolation so normal project generation is not re-routed.

## Output Shape

The output file is the manifest JSON itself, not a wrapper object. It includes at least:

```json
{
  "manifest_version": "1.0",
  "system_name": "...",
  "agents": [],
  "tools": [],
  "workflows": [],
  "memory": [],
  "permissions": {},
  "guardrails": [],
  "test_cases": []
}
```

The orchestrator adapter returns a small CTCP result object to stdout for command evidence, but writes the manifest JSON to the requested output path.

## Current Limits

- The generator is deterministic and signal-based.
- It is not an LLM-backed planner yet.
- Benchmarks cover structural, security, semantic, and holdout behavior.
- Benchmarks do not prove open-ended planning quality for every possible agent design request.

## Next Step: Scaffold Generation

After a manifest exists, use `agent-scaffold` to generate a minimal dry-run scaffold:

```powershell
.\.venv\Scripts\python.exe scripts\ctcp_orchestrate.py `
  agent-scaffold `
  --manifest out\agent_manifest.json `
  --output-dir out\agent_project
```

See `docs/agent_scaffold_mode.md` for scaffold structure, dry-run behavior, permissions preservation, and generated tests.

## End-to-End Agent Project Pipeline

Use `agent-project` when the input is still a requirement file and CTCP should produce the manifest, scaffold, dry-run evidence, scaffold-test evidence, and pipeline reports in one explicit mode:

```powershell
.\.venv\Scripts\python.exe scripts\ctcp_orchestrate.py `
  agent-project `
  --input tests\agent_factory_benchmark\fixtures\input_devops_incident.json `
  --output-dir runs\agent_project_devops
```

`agent-project` does not replace ordinary CTCP project generation and does not trigger unless the subcommand is present. See `docs/agent_project_pipeline.md`.

## Regression Commands

```powershell
.\.venv\Scripts\python.exe tests\agent_factory_benchmark\run_benchmark.py
.\.venv\Scripts\python.exe -m unittest tests.test_agent_manifest_orchestrator_integration -v
.\.venv\Scripts\python.exe -m unittest tests.test_agent_manifest_consumer -v
.\.venv\Scripts\python.exe -m unittest tests.test_agent_scaffold_integration -v
.\.venv\Scripts\python.exe -m unittest tests.test_agent_project_pipeline -v
.\.venv\Scripts\python.exe -m unittest tests.test_agent_project_orchestrator_e2e -v
.\.venv\Scripts\python.exe -m unittest tests.test_agent_manifest_generator -v
```
