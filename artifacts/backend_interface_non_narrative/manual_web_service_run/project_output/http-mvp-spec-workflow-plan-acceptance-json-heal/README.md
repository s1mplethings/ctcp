# 生成一个本地 HTTP 服务 MVP：接收模糊项目目标，返回结构化 spec、workflow plan、acceptance 摘要 JSON，并提供 health 检查。

This web service MVP exposes a local HTTP-style response contract and returns spec/workflow/acceptance JSON payloads. Use `--serve` for a health preview.

## Quick Start

`python scripts/run_project_web.py --serve`

## Repo Context Consumed

- artifacts/frontend_uploads/brief.txt
- docs/backend_interface_contract.md
- scripts/project_generation_gate.py
- scripts/project_manifest_bridge.py
- workflow_registry/wf_project_generation_manifest/recipe.yaml
