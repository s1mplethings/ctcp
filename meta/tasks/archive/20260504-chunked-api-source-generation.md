# Task Archive - Chunked API Source Generation

## Queue Binding

- Queue Item: `ADHOC-20260504-chunked-api-source-generation`
- Layer/Priority: `L1 / P0`
- Date: `2026-05-04`
- Status: `done`

## Scope

Keep API as the text producer, but split formal source generation into manifest and file-content batch calls that local code merges and validates.

## Evidence

- New module: `llm_core/providers/api_source_chunking.py`.
- Source-generation routing: `llm_core/providers/api_provider.py`.
- Prompt alignment: `ctcp_adapters/source_generation_prompt.py`.
- Tests:
  - `tests/test_api_source_chunking.py`
  - `tests/test_api_agent_templates.py -k source_generation`
  - `tests/test_project_generation_artifacts.py -k chunked_source_generation`
- Code health growth guard passed after splitting logic into the new module.

## Outcome

Formal `chair/source_generation` now defaults to chunked API text generation after `output_contract_freeze`: manifest-only first, then small file-content batches, then local merge into the existing provider source bundle path.
