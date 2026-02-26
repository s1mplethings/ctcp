# External Research - Popular Engineering Workflow Baseline (2026-02-26)

## Scope
- Build a "current mainstream workflow" baseline for comparison with CTCP.
- Source preference: official docs/reports.

## Sources
- DORA 2024 highlights (Google Cloud): https://cloud.google.com/blog/products/devops-sre/announcing-the-2024-dora-report
- GitHub protected branches / merge queue: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- GitHub flow / git workflows: https://docs.github.com/get-started/getting-started-with-git/git-workflows
- GitLab MR workflow and acceptance criteria: https://docs.gitlab.com/development/contributing/merge_request_workflow/
- Trunk-Based Development (short-lived branches): https://trunkbaseddevelopment.com/short-lived-feature-branches/
- Trunk-Based Development (CI): https://trunkbaseddevelopment.com/continuous-integration/
- CNCF 2025 annual survey announcement (published 2026-01-20): https://www.cncf.io/announcements/2026/01/20/kubernetes-established-as-the-de-facto-operating-system-for-ai-as-production-use-hits-82-in-2025-cncf-annual-cloud-native-survey/

## Extracted Signals (for process design)
1. AI-assisted development is mainstream, but AI alone does not improve delivery outcomes without small batches + strong testing.
2. Branch protection has become policy-heavy and automation-heavy:
   - required status checks
   - linear history options
   - merge queue for high-traffic branches
3. "Small change, fast review, fast merge" is emphasized:
   - short-lived branches
   - MR/PR size control
   - explicit acceptance checklist
4. Platform engineering + GitOps are associated with higher operational maturity in large-scale environments.
5. Cultural/system factors (DX, trust, communication) are now a key bottleneck, not only technical toolchains.

## Notes For CTCP Comparison
- CTCP already has strong contract/gate artifacts and auditable verification.
- Mainstream systems often optimize "path-to-merge" and dynamic policy enforcement in hosted forges.
- CTCP can likely improve by adding merge-queue-like concepts, PR size/SLO policy, and AI contribution trust controls.
