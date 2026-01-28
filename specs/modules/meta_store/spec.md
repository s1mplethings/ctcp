
# MetaStore

## Purpose
读写 `meta/pipeline_graph.json`（权威关系层），支持 GUI 编辑边并落盘。

## Inputs
- meta_path
- edit operations（add/remove/update edge、update node phase、save positions…）

## Outputs
- meta_graph object（供 GraphBuilder 使用）
- pipeline_graph.json（落盘）

## Process
- 读入：若文件不存在，生成最小骨架
- 写入：原子写（tmp + rename）
- 版本：meta 文件包含 schema_version

## Acceptance Criteria
- Given 一个工程无 meta 文件
- When load()
- Then 自动生成最小 meta
- And When editEdge(add)
- Then meta 文件内容更新并可再次 load

## Trace Links
- specs/contract_output/meta_pipeline_graph.schema.json
- docs/06_graph_map.md
- docs/05_navigation.md
