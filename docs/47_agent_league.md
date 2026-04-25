# Agent League

Agent League is a post-benchmark review layer for CTCP project-generation runs.

It does not replace `formal_basic_benchmark` or `formal_hq_benchmark`. The benchmark remains the hard gate. Agent League runs after a benchmark has passed or is close enough to inspect, and it looks for quality gaps, gray-area failures, and fake-success patterns that a binary benchmark can miss.

## Purpose

Agent League answers a different question from the benchmark:

- Benchmark: did the required gates pass?
- Agent League: would different reviewers trust the product and evidence?

The league is intentionally checklist-driven. Each role uses a fixed rubric and a role-specific input slice so results are comparable across runs.

## Roles

### Customer Agent

Role: realistic customer / buyer.

Inputs:

- benchmark case
- persona and scripted turns
- support transcript
- final screenshots
- final bundle summary

Outputs:

- `customer_review.md`
- `customer_score` from 0 to 25
- key positives and complaints
- satisfaction verdict

### Product Reviewer Agent

Role: product manager / product reviewer.

Inputs:

- `artifacts/project_spec.json`
- `artifacts/output_contract_freeze.json`
- feature matrix
- page map
- data model summary
- screenshots
- README
- final package tree

Outputs:

- `product_review.md`
- `product_score` from 0 to 25
- page, capability, and product-depth findings
- benchmark-tier fit verdict

### QA / Adversarial Agent

Role: QA / red-team reviewer.

Inputs:

- acceptance ledger and triplets
- `step_meta.jsonl`
- `events.jsonl`
- `api_calls.jsonl`
- `artifacts/verify_report.json`
- `artifacts/support_public_delivery.json`
- replay result

Outputs:

- `qa_findings.md`
- `qa_score` from 0 to 25
- blocker status
- first suspicious point
- fake-success / hidden-failure conclusion

### Delivery Critic Agent

Role: delivery acceptance reviewer.

Inputs:

- `artifacts/final_project_bundle.zip` content tree
- `artifacts/intermediate_evidence_bundle.zip` content tree
- README
- startup steps
- screenshots
- delivery manifests

Outputs:

- `delivery_review.md`
- `delivery_score` from 0 to 25
- delivery readiness verdict
- handoff gap list

## Fixed Order

The first implementation is sequential for stability:

1. Customer Agent
2. Product Reviewer Agent
3. QA / Adversarial Agent
4. Delivery Critic Agent

Parallel or remote-LLM judging can be added later, but the baseline must remain deterministic and replayable.

## Scoring

Total score: 100.

- Customer Agent: 25
- Product Reviewer Agent: 25
- QA / Adversarial Agent: 25
- Delivery Critic Agent: 25

Each role reads one structured checklist under `agent_league_cases/`.

## Overall Verdict

`PASS` requires:

- benchmark hard gate passed
- total score >= 80
- QA has no major blocker
- Delivery Critic says deliverable is portable enough to hand off

`PARTIAL` means:

- benchmark passed, but total score is 60-79
- or clear quality issues exist without a hard blocker

`FAIL` means:

- benchmark did not pass
- or total score < 60
- or QA found major fake success / hidden failure
- or Delivery Critic judged the project not deliverable

## Output Directory

By default, `scripts/run_agent_league.py` writes under:

```text
<run_dir>/artifacts/agent_league/
```

Required outputs:

- `customer_review.md`
- `product_review.md`
- `qa_findings.md`
- `delivery_review.md`
- `agent_league_summary.json`
- `agent_league_summary.md`

## Relationship To Formal Benchmarks

Use this order:

1. Run `formal_basic_benchmark` or `formal_hq_benchmark`.
2. Confirm the benchmark summary verdict.
3. Run Agent League on the run directory.
4. Report benchmark verdict and league verdict separately.

Benchmark PASS is still the hard gate. Agent League adds review depth and issue discovery; it does not turn a failed benchmark into a pass.
