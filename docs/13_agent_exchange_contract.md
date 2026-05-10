# Agent Exchange Contract

Scope boundary:
- This file is the authoritative contract for role-to-role handoff packets in CTCP agent execution.
- It defines the compact exchange payload used by Virtual Team Lane and TeamNet dispatch.
- It does not replace `artifacts/context_pack.json`, the support whiteboard, or the Virtual Team Lane artifact gate.

## 1) Purpose

The exchange packet exists to stop downstream agents from reconstructing product, architecture, implementation, and QA decisions from broad prompt prose.

Target behavior:
- each role records the decision it just made
- each role declares the context or MCP-style evidence it needs
- the next role receives bounded handoff instructions
- the packet is persisted in run artifacts and rendered into provider prompts
- malformed or absent packets do not block legacy dispatch behavior

## 2) Schema

Schema version: `ctcp-agent-exchange-v1`

Required top-level fields:
- `schema_version`
- `lane`
- `stage`
- `role`
- `goal`
- `decisions`
- `handoff`

Optional top-level fields:
- `input_refs`
- `context_needs`
- `assumptions`
- `open_questions`
- `risks`
- `acceptance_hooks`
- `evidence`

Canonical JSON shape:

```json
{
  "schema_version": "ctcp-agent-exchange-v1",
  "lane": "virtual_team",
  "stage": "architecture",
  "role": "solution_architect",
  "goal": "optimize project generation flow",
  "input_refs": ["docs/12_virtual_team_contract.md"],
  "context_needs": [
    {
      "kind": "repo",
      "query": "dispatch prompt handoff contract",
      "reason": "next role needs current prompt injection rules",
      "budget": {"max_files": 6, "max_total_bytes": 12000}
    }
  ],
  "decisions": ["Use dispatch whiteboard as the first packet transport."],
  "assumptions": ["Missing packet keeps legacy dispatch behavior."],
  "open_questions": ["Whether a later task should materialize context_needs through a broker."],
  "risks": ["Packet bloat can weaken provider prompt focus."],
  "handoff": {
    "next_role": "ux_designer",
    "next_required_artifact": "ux_flow.md",
    "must_preserve": ["single run truth remains in run_dir artifacts"],
    "must_not_do": ["do not add provider credentials or live API calls"]
  },
  "acceptance_hooks": ["prompt contains AGENT_EXCHANGE"],
  "evidence": ["artifacts/support_whiteboard.json"]
}
```

## 3) Field Semantics

- `lane`: execution lane. For design-heavy work this is `virtual_team`.
- `stage`: current team stage such as `intent`, `product`, `architecture`, `ux`, `implementation`, `qa`, or `delivery`.
- `role`: current producer role.
- `goal`: compact task goal, not a full transcript.
- `input_refs`: artifact or doc paths consumed by this role.
- `context_needs`: requested evidence for a later broker or librarian step; it is not direct permission for arbitrary tool calls.
- `decisions`: decisions made by this role that downstream roles must preserve.
- `assumptions`: bounded defaults used to avoid unnecessary user questions.
- `open_questions`: unresolved decisions that are still blocking or intentionally deferred.
- `risks`: known failure modes to watch.
- `handoff`: next owner, next artifact, preserved constraints, and forbidden moves.
- `acceptance_hooks`: tests, gates, or evidence that prove the handoff was consumed.
- `evidence`: paths or run artifacts supporting the packet.

## 4) Runtime Rules

- Exchange packets are optional for legacy Delivery Lane dispatch.
- Virtual Team Lane implementation handoff SHOULD include an exchange packet once this contract is active in the run path.
- A packet MUST be compact. Runtime renderers may truncate fields and list lengths.
- A packet MUST NOT contain secrets, provider credentials, full transcripts, or raw external data dumps.
- `context_needs` records what evidence is needed; the context broker or librarian decides how to satisfy it within budget.
- Downstream agents MUST treat `decisions`, `must_preserve`, and `must_not_do` as stronger than freeform prompt suggestions.
- A malformed packet is ignored or sanitized; it is not a reason to claim task completion.

## 5) Mainline Integration

Initial mainline integration is deliberately narrow:

1. Dispatch requests MAY include `agent_exchange`.
2. `dispatch_whiteboard` persists a sanitized `agent_exchange` entry.
3. Provider prompts render an `AGENT_EXCHANGE` section when packet data is present.
4. Tests prove the packet is connected and consumed.

Future work may add a context broker that materializes `context_needs` into `context_pack` inputs. That broker must remain a separate task because it changes provider/tool execution behavior.
