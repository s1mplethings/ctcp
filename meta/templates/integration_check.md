# Integration Check

Scope boundary: wiring proof only. Purpose and flow authorities remain `docs/01_north_star.md` and `docs/04_execution_flow.md`.

## Feature
- name:
- purpose:

## Wiring
- upstream:
- current_module:
- downstream:
- source_of_truth:
- fallback:
- acceptance_test:
- forbidden_bypass:
- user_visible_effect:

## Memory
- should_record_issue_memory: yes/no
- issue_capture_trigger:
- regression_test:

## Skill
- reusable_workflow: yes/no
- skillized: yes/no
- if_no_why:

## Verification
- unit_test:
- integration_test:
- end_to_end_test:
- user_visible_expected_behavior:

## Completion
- [ ] reachable from intended entrypoint
- [ ] consumed by intended downstream stage
- [ ] no parallel bypass path
- [ ] issue memory decision recorded
- [ ] skill decision recorded
- [ ] regression verified
