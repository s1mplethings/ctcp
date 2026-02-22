# B032 apply-patch-first-cli-entry

## Reason
- CLI entry for patch-first safe apply helper.

## Behavior
- Trigger: CLI execution of scripts/apply_patch_first.py.
- Inputs / Outputs: patch text + optional policy -> patch apply result json.
- Invariants: Policy validation runs before git apply and rejects unsafe paths.

## Result
- Acceptance: Exit code reflects env/policy/apply outcome contract.
- Evidence: scripts/apply_patch_first.py,tools/patch_first/core.py
- Related Gates: patch_check

