# Task - vn-business-project-generation-mainline

Archived because the active topic moved from “固定 VN 业务项目生成主链” to “project-generation contract mode separation”.

## Queue Binding

- Queue Item: `ADHOC-20260403-vn-business-project-generation-mainline`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Archived Summary

- Baseline previously bound: `faeaedbd419aeb9de182c606cd7ce27eaa091e89` / `3.3.4`
- Previous scope: 让固定 VN 请求通过主链产出真实业务代码，并把 `context_pack.json` 变成被消费的生成输入。
- Archived reason: 当前实现已经打通固定 VN 样题主链，但权威 project-generation contract 仍缺少 production 与 benchmark 的边界定义，容易把固定 VN 回归样题误读成 production 默认目标。

## Prior Evidence Snapshot

- `source_generation` 已要求 `consumed_context_pack=true`。
- `project_generation_gate` 和 manual VN runner 已验证业务文件、交付清单和上下文消费。
- `get_project_manifest` 已暴露业务生成相关字段。

## Open Gap Handed Off

- 权威 contract 仍未显式区分 production mode 与 benchmark / regression mode。
- 固定 VN 样题的定位尚未被写死为“仅用于 benchmark / regression”。
- gate 文案尚未分层说明 structural / behavioral / result completion。
