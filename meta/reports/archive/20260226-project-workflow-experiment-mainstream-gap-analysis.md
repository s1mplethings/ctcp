# Update 2026-02-26 (project workflow experiment + mainstream gap analysis)

### Goal
- Read project markdown/process structure, run one full repo workflow experiment, compare CTCP flow with current mainstream engineering workflows, and propose concrete improvements.

### Readlist
- Inventory scan: `rg --files -g "*.md"` => `333` markdown files discovered.
- Deep-read mandatory contracts/docs:
  - `AGENTS.md`
  - `ai_context/00_AI_CONTRACT.md`
  - `ai_context/CTCP_FAST_RULES.md`
  - `README.md`
  - `BUILD.md`
  - `PATCH_README.md`
  - `TREE.md`
  - `docs/00_CORE.md`
  - `docs/03_quality_gates.md`
  - `ai_context/problem_registry.md`
  - `ai_context/decision_log.md`
- Deep-read process docs/scripts:
  - `docs/02_workflow.md`
  - `docs/10_workflow.md`
  - `docs/10_team_mode.md`
  - `docs/21_paths_and_locations.md`
  - `docs/22_teamnet_adlc.md`
  - `docs/22_agent_teamnet.md`
  - `docs/30_artifact_contracts.md`
  - `docs/adlc_pipeline.md`
  - `docs/verify_contract.md`
  - `scripts/verify_repo.ps1`
  - `scripts/verify_repo.sh`
  - `scripts/workflow_checks.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/contract_checks.py`
  - `scripts/sync_doc_links.py`
- External baseline research:
  - `meta/externals/20260226-popular-dev-workflows.md`

### Plan
1) Docs/Spec: read mandatory contracts and workflow docs/scripts, map actual gate order.
2) Research-first: collect current mainstream workflow references (official docs/reports).
3) Verify experiment: run only `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`.
4) Report: write Readlist/Plan/Changes/Verify/Questions/Demo + gap analysis and improvements.

### Changes
- Files changed:
  - `meta/tasks/CURRENT.md`
  - `meta/externals/20260226-popular-dev-workflows.md`
  - `meta/reports/LAST.md`
- Key updates:
  - task card switched to current workflow-comparison experiment.
  - external mainstream workflow baseline added with sources.
  - report expanded with auditable verify result and process-gap recommendations.

### Verify
- Precheck:
  - `python scripts/workflow_checks.py` => exit `0`
  - `python scripts/plan_check.py` => exit `0`
  - `python scripts/patch_check.py` => exit `0`
- Acceptance gate:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `1`
  - First failure gate: `lite scenario replay`
  - Replay summary (initial run):
    - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260226-141246/summary.json`
    - `total=11, passed=7, failed=4`
  - Replay summary (final recheck):
    - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260226-141738/summary.json`
    - `total=11, passed=7, failed=4`
    - failed scenarios: `S13`, `S14`, `S17`, `S19`
  - First failed scenario in summary order:
    - `S13_lite_dispatch_outbox_on_missing_review`
    - error: `step 4: expect_exit mismatch, rc=1, expect=0`
    - assertion shows missing `reviews/review_contract.md` in orchestrated sandbox run.
- Minimal repair direction (scoped to first failure):
  - stabilize S13 contract review artifact generation path/timing so `review_contract.md` exists before assertion step.
  - then re-run `python simlab/run.py --suite lite` before re-running `scripts/verify_repo.ps1`.

### Gap Analysis (CTCP vs mainstream workflow)
1) Strength where CTCP is ahead:
   - Contract-first artifacts + auditable evidence chain (`TRACE.md`, `verify_report.json`, failure bundle).
   - Strict gate discipline and anti-pollution checks are stronger than many typical repo setups.
2) Gap 1: path-to-merge efficiency controls are weaker:
   - Mainstream (GitHub/GitLab) emphasizes branch protection + required checks + merge queue.
   - CTCP has strong verification, but limited explicit merge-queue/PR-size governance in docs/gates.
3) Gap 2: AI-era trust controls are not yet explicit enough:
   - DORA 2024 shows AI benefits depend on testing discipline and process quality.
   - CTCP has verification gates, but lacks explicit "AI contribution risk tier" policy in workflow contracts.
4) Gap 3: platform/DX operationalization is implicit:
   - Mainstream trends (DORA/CNCF) stress platform engineering and reduced cognitive load.
   - CTCP has many contracts and steps; operator cognitive load may be high without layered UX/automation modes.
5) Gap 4: failure localization in replay suites:
   - Current verify output surfaces replay summary, but first-failure diagnosis still needs manual drill-down to scenario traces.

### Improvement Plan (prioritized)
1) Add merge-queue-style policy gate:
   - Introduce a lightweight gate policy doc + check for "required checks complete before integration".
2) Add PR/patch size and lead-time guardrail:
   - enforce max touched files/added lines per change theme (already partly in patch policy, extend to merge policy).
3) Add AI contribution policy tier:
   - e.g., `ai_generated_change: low|medium|high risk` with mandatory extra checks for medium/high.
4) Improve replay failure observability:
   - emit "first failed scenario id + failing step + trace path" directly in `verify_repo` output.
5) Introduce two operating lanes:
   - `strict-audit` (current full contracts) and `fast-delivery` (reduced ceremony, same core safety gates).

### External References (used for mainstream baseline)
- DORA 2024 highlights (Google Cloud): https://cloud.google.com/blog/products/devops-sre/announcing-the-2024-dora-report
- GitHub protected branches: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- GitHub workflows: https://docs.github.com/get-started/getting-started-with-git/git-workflows
- GitLab MR workflow: https://docs.gitlab.com/development/contributing/merge_request_workflow/
- Trunk-based short-lived branches: https://trunkbaseddevelopment.com/short-lived-feature-branches/
- Trunk-based CI: https://trunkbaseddevelopment.com/continuous-integration/
- CNCF annual survey announcement (2026-01-20): https://www.cncf.io/announcements/2026/01/20/kubernetes-established-as-the-de-facto-operating-system-for-ai-as-production-use-hits-82-in-2025-cncf-annual-cloud-native-survey/

### Questions
- None (no credential/permission/mutually-exclusive blocking decision required).

### Demo
- Report: `meta/reports/LAST.md`
- Task card: `meta/tasks/CURRENT.md`
- Mainstream baseline research: `meta/externals/20260226-popular-dev-workflows.md`
- Verify evidence:
  - `scripts/verify_repo.ps1` command output in terminal (exit `1`)
  - replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260226-141738/summary.json`

