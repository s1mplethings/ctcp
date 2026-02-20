# PLAN

- Goal: Self improve core loop
- Round: 1
- Task limit: <= 5
- File change limit: <= 3 files

## Tasks
1. Confirm failure class from latest verify logs.
2. Use Local Librarian references to scope one minimal fix.
3. Generate unified diff patch with evidence references.
4. Run contract guard before/after patch apply.
5. Run verify_repo and update fix brief if failed.

## Candidate Files (max 3)
- `scripts/workflows/adlc_self_improve_core.py`
- `tools/contrast_rules.py`
- `tools/contract_guard.py`

## Acceptance Commands
- `python -m unittest discover -s tests -p "test_*.py"`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (Windows)
- `bash scripts/verify_repo.sh` (Linux/macOS)
