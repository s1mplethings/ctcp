# Externals Review — Graph Declutter / Rendering Options

## Goal
- Make dense graphs readable and interactive (reduce edge clutter) in `web/graph_spider`.

## Constraints
- Offline only?: Prefer yes; must load from Qt `qrc:/`.
- License constraints?: Prefer permissive.
- Must be vendorable?: Yes.
- Keep single implementation?: Yes — only `web/graph_spider/` owns the real graph implementation.

## Candidates
### A) Keep current Canvas renderer + add declutter modes
- Link: N/A
- Pros:
  - No dependency / no rewrite.
  - Works with existing Bridge and data model.
  - Fast for medium graphs.
- Cons:
  - Feature work stays on us (bundling, advanced layouts).
- Decision: Use now (add edge modes + budgets).

### B) cytoscape.js
- Link: https://js.cytoscape.org/
- License: MIT
- Pros:
  - Rich graph features, filtering, styles, plugins.
- Cons:
  - Larger rewrite; may require careful performance tuning in WebEngine.
- Decision: Consider later if we outgrow Canvas.

### C) sigma.js
- Link: https://www.sigmajs.org/
- License: MIT
- Pros:
  - Good performance; designed for large graphs.
- Cons:
  - Rewrite rendering + interactions; need layout integration.
- Decision: Consider later.

### D) force-graph (3d-force-graph / 2d)
- Link: https://github.com/vasturiano/force-graph
- License: MIT
- Pros:
  - Nice force simulation + rendering.
- Cons:
  - Depends on three.js in some variants; adds weight.
- Decision: Not now.

## Final pick
- Chosen: Enhance current Canvas renderer with explicit declutter controls:
  - Edge modes: `All`, `Smart`, `Tree`, `Neighbors`
  - Edge budget threshold for Smart mode
  - Hide directory `contains` edges by default
  - Keep optional “path-only on selection” behavior

## Notes
- If we later switch libraries, keep the Bridge contract (`requestGraph`, `setSelectedNode`, `commandRequested`) stable and change only the frontend implementation.
