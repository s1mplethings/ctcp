# Externals Review — UI Control Panel (Graph Spider)

## Goal
- Reduce topbar clutter and improve usability/maintainability of controls (Depth/View/edge declutter/physics) in `web/graph_spider`.

## Constraints
- Offline only?: Prefer yes (no CDN); must work from Qt `qrc:/`.
- License constraints?: Prefer permissive (MIT/BSD/Apache-2.0).
- Must support Windows?: Yes (Qt WebEngine embedded).
- Must be vendorable?: Yes (copy JS/CSS into `web/graph_spider/vendor/` and add to QRC).

## Candidates
### A) Tweakpane
- Link: https://cocopon.github.io/tweakpane/
- License: MIT
- Activity: active (popular, maintained)
- Bundle size / deps: small; no heavy deps
- Integration plan (exact files / APIs): vendor `tweakpane.min.js` into `web/graph_spider/vendor/`; build controls as a Pane bound to a config object; emit callbacks to update `CFG` and trigger `draw()` / `setRoot()`.
- Pros:
  - Great UX, good grouping/folders, good for many knobs.
  - Easy to bind to an object model.
- Cons:
  - Additional dependency; needs vendoring + QRC updates.
- Decision: Deferred (not yet needed for initial cleanup).

### B) lil-gui
- Link: https://lil-gui.georgealways.com/
- License: MIT
- Activity: active
- Bundle size / deps: very small; no deps
- Integration plan: vendor `lil-gui.min.js`; create GUI with folders; bind to `CFG`.
- Pros:
  - Lightweight, simple.
- Cons:
  - UI aesthetic is “debug panel”; may not match product feel.
- Decision: Deferred.

### C) dat.gui (legacy)
- Link: https://github.com/dataarts/dat.gui
- License: Apache-2.0
- Activity: mostly legacy
- Pros: well-known
- Cons: older styling + slower evolution
- Decision: Reject (prefer more modern options).

### D) Native HTML (details/summary + CSS)
- Link: N/A
- License: N/A
- Integration plan:
  - Use `<details>` / `<summary>` as a compact “Controls” popover.
  - Keep element IDs stable so existing JS wiring continues to work.
- Pros:
  - Zero dependency; works offline; easiest to ship via QRC.
- Cons:
  - Less “app-like” than a dedicated control panel library.
- Decision: Choose for this iteration.

## Final pick
- Chosen: Native HTML controls (details/summary)
- Why:
  - Meets offline/QRC constraints with zero dependency.
  - Unblocks immediate UX issues (topbar clutter) while we stabilize interaction model.
- What code to copy / what API to call:
  - No external code. Use `edgeMode`, `edgeMax`, `containsEdges`, `pathOnly` inputs and keep wiring in `web/graph_spider/spider.js`.
