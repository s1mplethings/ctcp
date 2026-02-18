
# Problem Registry（问题记忆）

格式（每条）：
- Symptom:
- Repro:
- Root cause:
- Fix:
- Prevention:
- Tags:

---

- Symptom:
  Agent/patch claims "verified" but no reproducible evidence artifacts exist.
- Repro:
  Run build/test manually without saving structured logs/proof; results cannot be audited later.
- Root cause:
  Verification was script-fragmented and not bound to a hard evidence gate.
- Fix:
  Introduce `tools/run_verify.py` + `tools/adlc_gate.py` + evidence directory contract under `artifacts/verify/<timestamp>/`.
- Prevention:
  Enforce gate in `scripts/verify.*` and CI; no `proof.json` or `proof.result != PASS` means merge must fail.
- Tags:
  verify, gate, evidence, reproducibility
