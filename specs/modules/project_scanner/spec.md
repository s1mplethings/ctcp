
# ProjectScanner

## Purpose
识别一个工程根目录是否符合 SDDAI 结构，定位 docs/specs/scripts/ai_context/runs 等关键目录与入口文件。

## Inputs
- root_path: string（用户选择的工程目录）

## Outputs
- project_layout: object
  - docs_root
  - specs_root
  - scripts_root
  - ai_context_root
  - runs_root（可为空）
  - warnings[]

## Process
1) 扫描常见路径（docs/, specs/, scripts/, ai_context/）
2) 若缺失关键文件（00_overview 等），给 warnings 但不直接 fail（允许渐进）
3) 输出 layout，用于后续 Index/BuildGraph

## Acceptance Criteria
- Given 一个符合 SDDAI 目录结构的工程
- When scan(root)
- Then 能返回非空 docs_root/specs_root，并能定位至少一个 overview/workflow 文档

## Trace Links
- docs/01_architecture.md

## Detection Rules（必须实现）
1) Marker 优先（强）：
- `meta/sddai_project.json` / `.sddai/project.json` / `sddai.project.json`
2) 无 Marker 时用 Heuristic：
- docs_root：优先 `docs/` 含 `00_overview.md` 或 `02_workflow.md`；其次根目录直接含这些文件
- specs_root：优先 `specs/` 含 `modules/` 或 `contract_output/`
- scripts_root：`scripts/` 含 `verify_repo.ps1` 或 `verify_repo.sh`
- ai_context_root：`ai_context/` 含 `problem_registry.md` 或 `decision_log.md`
- runs_root：`runs/`（可缺省）
3) 多候选评分：见 docs/04_project_detection.md

## Outputs（补充字段）
- candidates[]: {path, score, reasons[]}
- chosen_root_reason
- mode: "full" | "doc_only"（缺 specs 时必须降级）
- specs/contract_input/project_marker.schema.json
- docs/05_navigation.md
