# Patch 0003: Click → Preview Window, Category Click → Drill-down (No Overlap)

## What this patch fixes
- Desktop users often don't trigger Cytoscape `dbltap`.
- If backend returns nodes without `position`, preset layout stacks everything at (0,0).
- Too many edges/labels make the view unreadable.

## Hard rules implemented
1) **Category node single click**: drill down into next layer (requestGraph)
2) **Normal node single click**: open a preview window (backend openPath/openNode)
3) **Hard fallback positions**: if positions coverage < 70%, JS assigns block-grid positions (A order) so nodes never overlap
4) **Edge filtering**:
   - Summary: only keep `aggregate` edges (max 12)
   - Docs: keep only `docs_link`
   - Others: hide `docs_link` and cap total edges

## Backend bridge API required (QWebChannel)
Expose one QObject as `bridge` (or `backend`) with methods:

- `requestGraph(view: string, focus: string) -> string (JSON)`  (async callback in QWebChannel)
- `openPath(path: string)`   (open new window preview)
- optional: `openNode(nodeId: string)`

Note: QWebChannel uses async callbacks from JS; signature in C++ should be:
`Q_INVOKABLE void requestGraph(const QString& view, const QString& focus, const QJSValue& callback);`
or in QtWebChannel style: third arg callback function called with JSON string.

