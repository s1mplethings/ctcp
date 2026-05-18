from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
SUMMARY_PATH = ROOT / "tests" / "provider_assisted_benchmark" / "generated" / "provider_assisted_summary.json"
RUNNER = ROOT / "tests" / "provider_assisted_benchmark" / "run_provider_assisted_benchmark.py"
REVIEW_PACK = ROOT / "meta" / "reports" / "REVIEW_PACK.md"
BLIND_SUMMARY_PATH = ROOT / "tests" / "live_provider_blind_matrix" / "generated" / "live_provider_blind_matrix_summary.json"
MEDIUM_SUMMARY_PATH = ROOT / "tests" / "live_provider_medium_project_benchmark" / "generated" / "live_provider_medium_project_summary.json"


def load_or_run_summary() -> dict[str, Any]:
    if SUMMARY_PATH.exists():
        try:
            doc = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
            if isinstance(doc, dict) and doc.get("status") == "passed":
                return doc
        except Exception:
            pass
    proc = subprocess.run([sys.executable, str(RUNNER)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    if proc.returncode != 0:
        raise AssertionError(proc.stdout + "\n" + proc.stderr)
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def ensure_provider_review_pack() -> Path:
    summary = load_or_run_summary()
    lines = [
        "# CTCP Provider-Assisted Review Pack",
        "",
        "## Provider Participation Summary",
        "| Case | Provider Used | Provider Authorship | Generated Files | Fallback Count | Runtime Valid |",
        "|---|---:|---|---|---:|---:|",
    ]
    for row in summary.get("projects", []):
        attr = row.get("attribution", {})
        validation = attr.get("provider_validation", {}) if isinstance(attr.get("provider_validation", {}), dict) else {}
        lines.append(
            f"| {row.get('case')} | `{attr.get('used_provider_agent')}` | `{attr.get('provider_authorship')}` | "
            f"`{', '.join(attr.get('provider_generated_files', []))}` | `{len(attr.get('provider_fallbacks', []))}` | "
            f"`{validation.get('runtime_valid')}` |"
        )
    lines.extend(
        [
            "",
            "## Deterministic Guardrails",
            "- Ordinary mainline remains `new-run/status/advance`.",
            "- Core structure, persistence, generated tests, and runtime validators remain deterministic.",
            "- Provider fragments are bounded, syntax checked, safety filtered, and fallback to deterministic output if invalid.",
            "",
            "## Benchmark Summary",
            f"- provider-assisted benchmark: `{summary.get('passed')}/{summary.get('total')}`",
            f"- report: `{ROOT / 'tests' / 'provider_assisted_benchmark' / 'benchmark_report.md'}`",
            f"- summary: `{SUMMARY_PATH}`",
            "",
            "## Reproduction Commands",
            "- `.\\.venv\\Scripts\\python.exe tests\\provider_assisted_benchmark\\run_provider_assisted_benchmark.py`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_provider_assisted_generation -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_provider_assisted_attribution -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_provider_assisted_fallback -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_provider_assisted_validation -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_provider_assisted_variation -v`",
            "",
            "## Risks For Human Review",
            "- Provider-assisted mode is fixture/local-provider backed in this phase; it is not autonomous provider-authored generation.",
            "- Deterministic fallback remains required for reproducibility.",
        ]
    )
    if BLIND_SUMMARY_PATH.exists():
        try:
            blind_summary = json.loads(BLIND_SUMMARY_PATH.read_text(encoding="utf-8"))
        except Exception:
            blind_summary = {}
        if blind_summary.get("status") == "passed":
            lines.extend(
                [
                    "",
                    "## Live Provider Blind Matrix Summary",
                    f"- status: `{blind_summary.get('status')}`",
                    f"- cases: `{blind_summary.get('case_count')}`",
                    f"- provider_request_count: `{blind_summary.get('provider_request_count')}`",
                    f"- provider_project_candidate_count: `{blind_summary.get('provider_project_candidate_count')}`",
                    f"- accepted/repaired/fallback/unsupported/failed: "
                    f"`{blind_summary.get('accepted_count')}/{blind_summary.get('repaired_count')}/"
                    f"{blind_summary.get('fallback_count')}/{blind_summary.get('unsupported_count')}/"
                    f"{blind_summary.get('failed_count')}`",
                    "",
                    "| Case | Outcome | Status |",
                    "|---|---|---|",
                ]
            )
            for row in blind_summary.get("cases", []):
                lines.append(f"| {row.get('project')} | `{row.get('outcome')}` | `{row.get('status')}` |")
    if MEDIUM_SUMMARY_PATH.exists():
        try:
            medium_summary = json.loads(MEDIUM_SUMMARY_PATH.read_text(encoding="utf-8"))
        except Exception:
            medium_summary = {}
        if medium_summary.get("status") == "passed":
            phase20 = medium_summary.get("phase20", {}) if isinstance(medium_summary.get("phase20", {}), dict) else {}
            lines.extend(
                [
                    "",
                    "## Phase 20 Acceptance Hardening Summary",
                    f"- new accepted/repaired/fallback counts: `{phase20.get('accepted_count')}/{phase20.get('repaired_count')}/{phase20.get('fallback_count')}`",
                    f"- acceptance_rate: `{phase20.get('acceptance_rate')}`",
                    f"- accepted_or_repaired_rate: `{phase20.get('accepted_or_repaired_rate')}`",
                    f"- gate passed: `{phase20.get('phase20_gate_passed')}`",
                    "- fixture lowering: `no`",
                    "",
                    "## Phase 21B Medium Candidate Recovery Summary",
                    f"- status: `{medium_summary.get('status')}`",
                    f"- cases: `{medium_summary.get('case_count')}`",
                    f"- accepted/repaired/fallback/failed: `{medium_summary.get('accepted_count')}/{medium_summary.get('repaired_count')}/{medium_summary.get('fallback_count')}/{medium_summary.get('failed_count')}`",
                    f"- provider request count: `{medium_summary.get('provider_request_count')}`",
                    f"- provider project candidate count: `{medium_summary.get('provider_project_candidate_count')}`",
                    "- ordinary mainline: `new-run/status/advance`",
                    "- agent-project/scaffold substitution: `no`",
                    "",
                    "| Case | Outcome | Provider Ratio | Runtime |",
                    "|---|---|---:|---:|",
                ]
            )
            for row in medium_summary.get("cases", []):
                lines.append(f"| {row.get('project')} | `{row.get('outcome')}` | `{row.get('provider_authored_file_ratio')}` | `{row.get('runtime_validation', {}).get('passed')}` |")
    REVIEW_PACK.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REVIEW_PACK
