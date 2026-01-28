
# RunLoader

## Purpose
读取 runs 目录，生成运行时状态：
- MVP：通过产物存在性推断步骤完成度
- Enhanced：读取 events.jsonl 精确时间线

## Inputs
- runs_root
- project_layout（用于定位关键产物的相对路径）

## Outputs
- run_state:
  - runs[]: {run_id, start_time, status, step_states[], outputs[]}
  - current_run（可选）

## Process
- MVP：根据关键产物存在性（transcription/segments/manifest 等）推断
- Enhanced：解析 events.jsonl（每行一个 event）

## Acceptance Criteria
- Given runs 目录包含至少一个 run
- When loadRuns()
- Then GUI 能显示 run 列表与卡点步骤

## Trace Links
- specs/contract_output/run_events.schema.json
- docs/06_graph_map.md
- docs/05_navigation.md
