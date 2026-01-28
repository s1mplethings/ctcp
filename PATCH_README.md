
# Patch: Summary + Drill-down + Mutable/Tier tagging

## What this patch adds
- Adds ViewManager spec (specs/modules/view_manager/spec.md)
- Adds Summary/Drill-down doc (docs/08_summary_drilldown.md)
- Extends schemas:
  - meta_pipeline_graph.schema.json: ui + tier/mutable/pinned/category + aggregate/weight
  - graph.schema.json: tier/mutable/pinned/collapsed/childrenCount/category + aggregate/weight
- Updates meta/pipeline_graph.json:
  - ui.default_view = Summary
  - ui.summary.categories/pinned/grid
  - tags modules/contracts with tier/mutable/pinned/category
- Updates docs navigation & layout rules

## Apply
- If this is a git repo: `git apply 0001_summary_drilldown_mutable.patch`
- Or manually copy the changed files listed in the patch.
