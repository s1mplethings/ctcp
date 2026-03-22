# Support Whiteboard Contract

## Purpose

The support whiteboard is a **shared append-only log** that records all significant events during a run's execution, enabling:
- Support bot to see what the backend has done (librarian lookups, dispatch results)
- Multi-agent dispatch results to be visible to support replies
- Progress tracking across support turns and backend execution

## Schema Version

`ctcp-support-whiteboard-v1`

## File Location

```
${run_dir}/artifacts/support_whiteboard.json
```

Where `${run_dir}` is typically `~/.ctcp/runs/ctcp/<run_id>/` (external to repo).

## Structure

```json
{
  "schema_version": "ctcp-support-whiteboard-v1",
  "entries": [
    {
      "ts": "2026-03-22T10:30:45Z",
      "role": "support | librarian | analyst | architect | coder | reviewer | tester | judge | worker",
      "kind": "support_turn | support_lookup | dispatch_result | dispatch_lookup",
      "text": "human-readable summary (max 260 chars)",
      "query": "optional: search query used for librarian lookup (max 220 chars)",
      "hits": [
        {
          "path": "relative/path/to/file.py",
          "start_line": 42,
          "score": 0.85
        }
      ],
      "hit_count": 4,
      "lookup_error": "optional: error message if lookup failed"
    }
  ]
}
```

## Entry Types

### `support_turn`
- **role**: `support`
- **kind**: `support_turn`
- **text**: `{source} {conversation_mode}: {user_text}` (max 260 chars)
- **query**: brief version of user text for librarian lookup (max 220 chars)
- Written by: `ctcp_dispatch.record_support_turn_whiteboard()`

### `support_lookup`
- **role**: `librarian`
- **kind**: `support_lookup`
- **text**: `lookup completed with {N} hits` or `lookup error: {error}`
- **query**: search query used
- **hits**: array of `{path, start_line, score}` (max 4 items)
- **hit_count**: total number of hits
- **lookup_error**: error message if lookup failed
- Written by: `ctcp_dispatch.record_support_turn_whiteboard()` (after librarian search)

### `dispatch_result`
- **role**: agent role (e.g., `analyst`, `architect`, `coder`, `reviewer`)
- **kind**: `dispatch_result`
- **text**: `{role}/{action} via {provider} => {status} ({target_path}); {reason}`
- Written by: `ctcp_dispatch._append_dispatch_result_whiteboard()` after each agent execution

### `dispatch_lookup`
- **role**: `librarian`
- **kind**: `dispatch_lookup`
- **text**: `dispatch lookup for {role}/{action}: {query}`
- **query**: search query derived from dispatch request
- **hits**: array of `{path, start_line, score}` (max 5 items)
- Written by: `ctcp_dispatch._prepare_dispatch_whiteboard_context()`

## Writers

| Function | Location | What it writes |
|----------|----------|----------------|
| `record_support_turn_whiteboard()` | `scripts/ctcp_dispatch.py:290` | `support_turn` + `support_lookup` entries |
| `_append_dispatch_result_whiteboard()` | `scripts/ctcp_dispatch.py:454` | `dispatch_result` entries after agent execution |
| `_prepare_dispatch_whiteboard_context()` | `scripts/ctcp_dispatch.py:382` | `dispatch_lookup` entries before agent execution |

## Readers

| Function | Location | What it reads |
|----------|----------|---------------|
| `get_support_whiteboard_context()` | `scripts/ctcp_dispatch.py:277` | Returns snapshot (last 5 entries) + latest librarian context |
| `ctcp_get_support_context()` | `scripts/ctcp_front_bridge.py:279` | Calls `get_support_whiteboard_context()` and returns full support context |
| `build_progress_binding()` | `scripts/ctcp_support_bot.py:1250` | Extracts `done_items` from whiteboard entries for progress reply |
| `_whiteboard_snapshot_entries()` | `scripts/ctcp_support_bot.py:1235` | Extracts entries from `project_context["whiteboard"]["snapshot"]` |

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ User sends message to support bot                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ ctcp_support_bot.sync_project_context()                         │
│   → ctcp_front_bridge.ctcp_record_support_turn()                │
│     → ctcp_dispatch.record_support_turn_whiteboard()            │
│       → Writes: support_turn entry                              │
│       → Calls: local_librarian.search()                         │
│       → Writes: support_lookup entry (with hits)                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ ctcp_front_bridge.ctcp_advance() (if project turn)              │
│   → ctcp_orchestrate.py advance                                 │
│     → ctcp_dispatch.dispatch_once()                             │
│       → _prepare_dispatch_whiteboard_context()                  │
│         → Writes: dispatch_lookup entry                         │
│       → {provider}.execute() (api_agent/ollama/codex/etc)       │
│       → _append_dispatch_result_whiteboard()                    │
│         → Writes: dispatch_result entry                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ ctcp_support_bot.build_progress_binding()                       │
│   → Reads whiteboard snapshot from project_context              │
│   → Extracts done_items: "资料检索已跑过一轮", "{label}已跑过一轮" │
│   → Injects into support prompt                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Support bot generates reply with grounded progress info         │
└─────────────────────────────────────────────────────────────────┘
```

## Constraints

- **Max entries**: 120 (enforced by `_safe_whiteboard_entries()`)
- **Max hits per lookup**: 4-5 (support: 4, dispatch: 5)
- **Text field max**: 260 chars (enforced by `_brief_text()`)
- **Query field max**: 220 chars
- **Reason field max**: 180 chars
- **Target path max**: 140 chars

## Snapshot Format

When `get_support_whiteboard_context()` is called, it returns a **snapshot** (last 5 entries) in this format:

```json
{
  "path": "artifacts/support_whiteboard.json",
  "query": "latest librarian query",
  "hits": [...],
  "lookup_error": "",
  "snapshot": {
    "schema_version": "ctcp-support-whiteboard-v1",
    "path": "artifacts/support_whiteboard.json",
    "entry_count": 12,
    "entries": [
      {
        "ts": "2026-03-22T10:30:45Z",
        "role": "support",
        "kind": "support_turn",
        "text": "telegram project_intake: 我想做一个帮我整理 VN 剧情结构的项目",
        "query": "我想做一个帮我整理 VN 剧情结构的项目"
      },
      {
        "ts": "2026-03-22T10:30:46Z",
        "role": "librarian",
        "kind": "support_lookup",
        "text": "lookup completed with 4 hits",
        "query": "我想做一个帮我整理 VN 剧情结构的项目",
        "hits": [
          {"path": "tools/scaffold.py", "start_line": 1}
        ],
        "hit_count": 4
      }
    ]
  }
}
```

## Integration with Support Bot

The whiteboard is consumed by support bot in two places:

1. **Progress binding** (`build_progress_binding()`):
   - Extracts `done_items` from `dispatch_result` entries with `status=executed`
   - Maps dispatch actions to user-facing labels (e.g., "file_request" → "资料检索")
   - Injects into support prompt as concrete progress evidence

2. **Prompt context** (via `project_context["whiteboard"]`):
   - Full snapshot is available in `project_context` passed to support provider
   - Support model can see recent backend activity

## Verification

To verify whiteboard is working:

1. Check file exists: `${run_dir}/artifacts/support_whiteboard.json`
2. Check entries are written after support turn: `record_support_turn_whiteboard()` called
3. Check entries are written after dispatch: `_append_dispatch_result_whiteboard()` called
4. Check support bot consumes whiteboard: `build_progress_binding()` extracts `done_items`

Regression tests:
- `tests/test_runtime_wiring_contract.py` — verifies support → bridge → whiteboard → support path
- `tests/test_support_bot_humanization.py` — verifies support replies consume whiteboard data

## Related Contracts

- `contracts/frontend_session_contract.md` — support session state
- `docs/10_team_mode.md` — support bot behavior
- `ai_context/problem_registry.md` Example 7 — whiteboard wiring fix history
