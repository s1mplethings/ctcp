# Default Mainline Freeze Contract

## Frozen Mainline

The frozen default CTCP runtime mainline is:

`goal/task input -> librarian/context_pack -> ADLC phase judgment + plan/gate -> execution lane -> whiteboard progress emission -> frontend/backend bridge consumption -> delivery/gate result -> run_manifest finalization`

This freeze protects the already-verified mainline that proves Librarian, ADLC, Whiteboard, and Bridge co-exist in the same run through `<run_dir>/artifacts/run_manifest.json`.

## Protected Mainline Surface

The protected surface is recorded in `artifacts/mainline_freeze_manifest.json`.
It includes the workflow contract, run-manifest contract, whiteboard/bridge integration contracts, runtime writer scripts, the shared manifest helper, and the integration tests that prove and protect the mainline.

## Default Rule After Freeze

These files are frozen by default.
Future patches MUST NOT modify protected files unless the user explicitly authorizes a mainline unfreeze.

Allowed user language includes:

- `解冻主线`
- `unfreeze the mainline`
- an equivalent explicit instruction that the default mainline freeze may be changed

## Required Future Change Procedure

If the default mainline must change later, the task must first explain:

1. why the current freeze no longer holds
2. which protected files must change
3. how the same-run proof through `run_manifest.json` will remain valid
4. which freeze manifest hashes will be regenerated

Without that explicit unfreeze and explanation, drift in the protected files is a test failure.

