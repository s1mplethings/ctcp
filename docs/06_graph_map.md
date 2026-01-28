
# Graph Map（图示：Doc ↔ Spec ↔ Contract）

## A) 关系图（概念层）
```mermaid
graph TD

  subgraph Docs
    D00[00_overview.md]
    D01[01_architecture.md]
    D02[02_workflow.md]
    D03[03_quality_gates.md]
    D04[04_project_detection.md]
    D11[11_webengine_resources.md]
    D20[20_conventions.md]
  end

  subgraph Specs
    MPS[ProjectScanner]
    MGB[GraphBuilder]
    MMS[MetaStore]
    MRL[RunLoader]
    MBR[QWebChannel Bridge]
    MWR[Web Renderer]
  end

  subgraph Contracts
    CGraph[graph.schema.json]
    CMeta[meta_pipeline_graph.schema.json]
    CRun[run_events.schema.json]
  end

  D00 --> D05[05_navigation.md]
  D00 --> D01
  D00 --> D02
  D00 --> D03
  D01 --> MPS
  D01 --> MGB
  D01 --> MMS
  D01 --> MRL
  D01 --> MBR
  D01 --> MWR
  D03 --> CGraph
  D03 --> CMeta
  D03 --> CRun

  MGB --> CGraph
  MMS --> CMeta
  MRL --> CRun
  D11 --> MWR
  D04 --> MPS
```

## B) 最小演示（GUI 的默认图建议）
- Docs：用 `docs_link` 连线（从 md 链接解析）
- Module ↔ Contract：用 `produces/consumes`（来自 spec IO 或 meta/pipeline_graph.json）
- Phase 分组：用 meta.modules.phase；缺失统一放 `Unassigned`
