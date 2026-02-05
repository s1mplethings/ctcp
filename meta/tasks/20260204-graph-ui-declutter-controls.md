# Task — Graph Spider: declutter controls + fix Details visibility

## Context
- Users report the graph is too dense (too many edges) and the topbar is crowded.
- Details window can appear blank because `spider.css` previously force-hid `#panel`.
- Navigation restore was subtly broken because `overview()` / `drillDown()` always pushed history even during Back/Forward restore.

## Acceptance (must be checkable)
- [ ] Details view renders (both embedded panel and `details.html`) with no CSS forcing `display:none` on `#panel`.
- [ ] `overview()` and `drillDown()` support `{push:false}` so Back/Forward does not create new history entries.
- [ ] Topbar no longer contains every control; advanced settings live under a single “Controls” dropdown.
- [ ] Edge declutter modes exist and are selectable:
  - `Smart` (default): draws full edges until edge budget; then falls back to tree + highlights
  - `All`
  - `Tree`
  - `Neighbors`
- [ ] `contains` (directory) edges are hidden by default but can be enabled.
- [ ] `scripts/verify_repo.ps1` or at minimum `scripts/verify.ps1` runs without new failures (environment-dependent).

## Plan
1) Research-first
   - `meta/externals/ui-control-panel.md`
   - `meta/externals/graph-declutter.md`
2) Implement
   - Fix CSS visibility bug
   - Refactor topbar to use `<details>` control popover
   - Add edge modes + edge budget + contains-edge toggle + path-only toggle
   - Fix history push behavior for restore
3) Verify
   - Quick open `details.html` in app and confirm it is visible
   - Smoke navigation Back/Forward

## Notes / Decisions
- Kept implementation in `web/graph_spider/` only.
- Deferred introducing Tweakpane/lil-gui until the interaction model stabilizes.

## Results
- Implemented in:
  - `web/graph_spider/index.html`
  - `web/graph_spider/spider.css`
  - `web/graph_spider/spider.js`
