# Live API-Only Tests

These tests validate CTCP multi-role contract linking with `api_agent` only.

## Preconditions

- `CTCP_LIVE_API=1`
- `OPENAI_API_KEY` (or `CTCP_OPENAI_API_KEY`)
- Optional: `OPENAI_BASE_URL` (defaults to `https://api.openai.com/v1`)

Live tests are skipped by default when the preconditions are not met.

## Commands

Smoke (all-role linked flow):

```powershell
$env:CTCP_LIVE_API="1"
$env:CTCP_FORCE_PROVIDER="api_agent"
$env:OPENAI_API_KEY="<your_key>"
python -m unittest tests.test_live_api_only_pipeline.LiveApiOnlyPipelineTests.test_api_linked_flow_smoke -v
```

Routing matrix:

```powershell
$env:CTCP_LIVE_API="1"
$env:CTCP_FORCE_PROVIDER="api_agent"
$env:OPENAI_API_KEY="<your_key>"
python -m unittest tests.test_live_api_only_pipeline.LiveApiOnlyPipelineTests.test_api_routing_matrix -v
```

Robustness faults:

```powershell
$env:CTCP_LIVE_API="1"
$env:CTCP_FORCE_PROVIDER="api_agent"
$env:OPENAI_API_KEY="<your_key>"
python -m unittest tests.test_live_api_only_pipeline.LiveApiOnlyPipelineTests.test_api_robustness_faults -v
```

Unified live test entry:

```powershell
python scripts/run_live_api_only_tests.py
```

`scripts/run_live_api_only_tests.py` will auto-load `OPENAI_API_KEY` and `OPENAI_BASE_URL`
from `.agent_private/NOTES.md` when env vars are not set locally.
