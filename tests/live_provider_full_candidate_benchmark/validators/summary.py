from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
SUMMARY_PATH = ROOT / "tests" / "live_provider_full_candidate_benchmark" / "generated" / "live_provider_full_candidate_summary.json"
RUNNER = ROOT / "tests" / "live_provider_full_candidate_benchmark" / "run_live_provider_full_candidate_benchmark.py"
REVIEW_PACK = ROOT / "meta" / "reports" / "REVIEW_PACK.md"


def load_or_run_summary() -> dict[str, Any]:
    if SUMMARY_PATH.exists():
        try:
            doc = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
            if isinstance(doc, dict) and doc.get("status") == "passed":
                return doc
        except Exception:
            pass
    proc = subprocess.run([sys.executable, str(RUNNER)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    if proc.returncode != 0:
        raise AssertionError(proc.stdout + "\n" + proc.stderr)
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def ensure_full_candidate_review_pack() -> Path:
    tests_dir = ROOT / "tests"
    if str(tests_dir) not in sys.path:
        sys.path.insert(0, str(tests_dir))
    from live_provider_full_candidate_benchmark.run_live_provider_full_candidate_benchmark import write_full_candidate_review_pack

    summary = load_or_run_summary()
    write_full_candidate_review_pack(summary)
    return REVIEW_PACK

