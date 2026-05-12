# Task Archive - External Agent Factory Benchmark

## Queue Binding

- Queue Item: `ADHOC-20260511-external-agent-factory-benchmark`
- Layer/Priority: `L1 / P0`
- Lane: `Delivery Lane`
- Status: done

## Summary

Created an external QA benchmark harness for six fixed agent-factory style scenarios. The harness invokes real CTCP workflow/project-generation code, writes generated outputs, and independently validates schema, permissions, workflow, and tools.

## Outputs

- `tests/agent_factory_benchmark/fixtures/*.json`
- `tests/agent_factory_benchmark/generated/*.json`
- `tests/agent_factory_benchmark/validators/*.py`
- `tests/agent_factory_benchmark/run_benchmark.py`
- `tests/agent_factory_benchmark/benchmark_report.md`

## Result

- Benchmark pass count: 0
- Benchmark fail count: 0
- Benchmark unsupported count: 6
- Unsupported reason: no discovered CTCP entrypoint produces an agent manifest with `agents`, `tools`, `permissions`, `workflows`, `guardrails`, and `test_cases`.

## Verify

- PASS: benchmark runner returned 0.
- PASS: benchmark runner/validators py_compile returned 0.
- PASS: workflow/module/patch/code-health focused gates returned 0 after evidence repair.
- PASS: canonical verify returned 0 with code profile, `CTCP_SKIP_LITE_REPLAY=1`, 550 Python unit tests run with 4 skipped, and triplet guard tests passing.
