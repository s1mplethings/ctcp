#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK_ZIP = ROOT / "plane_lite_team_pm_test_pack.zip"
CASE_ROOT = ROOT / "agent_league_cases"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_text(path: Path, limit: int = 20000) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:limit]


def load_case(name: str) -> dict[str, Any]:
    return read_json(CASE_ROOT / name)


def load_benchmark(zip_path: Path) -> dict[str, Any]:
    if not zip_path.exists():
        return {"case": {}, "files": {}, "missing": str(zip_path)}
    files: dict[str, str] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.endswith("/") or not name.lower().endswith((".md", ".json", ".txt")):
                continue
            files[name] = zf.read(name).decode("utf-8", errors="replace")
    case_name = next((name for name in files if name.endswith("benchmark_case.json")), "")
    case = json.loads(files[case_name]) if case_name else {}
    return {"case": case, "files": files}


def list_zip(path: Path, limit: int = 500) -> list[str]:
    if not path.exists():
        return []
    try:
        with zipfile.ZipFile(path) as zf:
            return sorted(zf.namelist())[:limit]
    except Exception:
        return []


def find_project_root(run_dir: Path) -> Path | None:
    project_output = run_dir / "project_output"
    if not project_output.exists():
        return None
    candidates = [path for path in project_output.iterdir() if path.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def find_transcript(run_dir: Path) -> tuple[str, list[str]]:
    candidates = sorted(run_dir.glob("*transcript*.md"))
    if candidates:
        return read_text(candidates[0]), [str(candidates[0])]
    support_inboxes = sorted(run_dir.parent.glob("support_sessions/*/artifacts/support_inbox.jsonl"))
    if support_inboxes:
        return read_text(support_inboxes[0]), [str(support_inboxes[0])]
    return "", []


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return len([line for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()])


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def collect_context(run_dir: Path, benchmark_zip: Path) -> dict[str, Any]:
    project_root = find_project_root(run_dir)
    transcript, transcript_sources = find_transcript(run_dir)
    final_zip = run_dir / "artifacts" / "final_project_bundle.zip"
    evidence_zip = run_dir / "artifacts" / "intermediate_evidence_bundle.zip"
    screenshots = []
    if project_root:
        screenshots = sorted(str(path.relative_to(project_root)) for path in (project_root / "artifacts" / "screenshots").glob("*.png"))
    readme = read_text(project_root / "README.md") if project_root else ""
    docs = {
        "feature_matrix": read_text(project_root / "docs" / "feature_matrix.md") if project_root else "",
        "page_map": read_text(project_root / "docs" / "page_map.md") if project_root else "",
        "data_model_summary": read_text(project_root / "docs" / "data_model_summary.md") if project_root else "",
    }
    support_delivery = read_json(run_dir / "artifacts" / "support_public_delivery.json")
    replay = support_delivery.get("replay_report", {}) if isinstance(support_delivery.get("replay_report"), dict) else {}
    api_rows = parse_jsonl(run_dir / "api_calls.jsonl")
    acceptance_root = run_dir / "artifacts" / "acceptance"
    triplet_dirs: list[str] = []
    missing_triplets: list[str] = []
    fallback_passed: list[str] = []
    if acceptance_root.exists():
        for child in acceptance_root.glob("**"):
            if not child.is_dir() or child == acceptance_root:
                continue
            present = [name for name in ("request.json", "result.json", "acceptance.json") if (child / name).exists()]
            if not present:
                continue
            rel = child.relative_to(acceptance_root).as_posix()
            if len(present) == 3:
                triplet_dirs.append(rel)
                result = read_json(child / "result.json")
                acceptance = read_json(child / "acceptance.json")
                if result.get("fallback_used") is True and acceptance.get("passed") is True:
                    fallback_passed.append(rel)
            else:
                missing_triplets.append(rel)
    return {
        "run_dir": run_dir,
        "benchmark": load_benchmark(benchmark_zip),
        "run": read_json(run_dir / "RUN.json"),
        "find_result": read_json(run_dir / "artifacts" / "find_result.json"),
        "project_spec": read_json(run_dir / "artifacts" / "project_spec.json"),
        "freeze": read_json(run_dir / "artifacts" / "output_contract_freeze.json"),
        "verify": read_json(run_dir / "artifacts" / "verify_report.json"),
        "support_delivery": support_delivery,
        "replay": replay,
        "extended_ledger": read_json(run_dir / "artifacts" / "extended_coverage_ledger.json"),
        "project_root": project_root,
        "readme": readme,
        "docs": docs,
        "screenshots": screenshots,
        "transcript": transcript,
        "transcript_sources": transcript_sources,
        "final_zip": final_zip,
        "evidence_zip": evidence_zip,
        "final_zip_tree": list_zip(final_zip),
        "evidence_zip_tree": list_zip(evidence_zip),
        "api_rows": api_rows,
        "acceptance": {
            "triplet_dirs": triplet_dirs,
            "missing_triplets": missing_triplets,
            "ledger_lines": count_lines(acceptance_root / "ledger.jsonl"),
            "fallback_passed": fallback_passed,
        },
        "step_meta_lines": count_lines(run_dir / "step_meta.jsonl"),
        "events_lines": count_lines(run_dir / "events.jsonl"),
    }


def add_check(findings: list[dict[str, Any]], case: dict[str, Any], check_id: str, passed: bool, evidence: str, issue: str = "") -> int:
    spec = next((item for item in case.get("checklist", []) if item.get("id") == check_id), {})
    points = int(spec.get("points", 0) or 0)
    awarded = points if passed else 0
    findings.append({
        "id": check_id,
        "label": spec.get("label", check_id),
        "points": points,
        "awarded": awarded,
        "passed": passed,
        "evidence": evidence,
        "issue": issue,
    })
    return awarded


def spec_domain_ok(ctx: dict[str, Any]) -> bool:
    freeze = ctx["freeze"]
    spec = ctx["project_spec"]
    return (
        (freeze.get("project_domain") or spec.get("project_domain")) == "team_task_management"
        and (freeze.get("project_type") or spec.get("project_type")) == "team_task_pm"
        and (freeze.get("project_archetype") or spec.get("project_archetype")) == "team_task_pm_web"
    )


def is_hq(ctx: dict[str, Any]) -> bool:
    freeze = ctx["freeze"]
    spec = ctx["project_spec"]
    return (freeze.get("build_profile") or spec.get("build_profile")) == "high_quality_extended"


def customer_agent(ctx: dict[str, Any]) -> dict[str, Any]:
    case = load_case("customer_persona_case.json")
    findings: list[dict[str, Any]] = []
    score = 0
    benchmark_case = ctx["benchmark"].get("case", {})
    score += add_check(findings, case, "goal_fit", spec_domain_ok(ctx), "spec/freeze domain/type/archetype", "Project freeze does not match team task PM.")
    readme_lower = ctx["readme"].lower()
    persona_ok = bool(ctx["readme"]) and any(token in ctx["readme"] for token in ("本地", "local", "启动", "start"))
    score += add_check(findings, case, "persona_fit", persona_ok, "README/startup text", "README/startup material is missing or not local-team oriented.")
    visible_ok = bool(ctx["transcript"] or ctx["events_lines"] or ctx["screenshots"])
    score += add_check(findings, case, "visible_progress", visible_ok, "transcript/events/screenshots", "No visible progress evidence found.")
    confidence_ok = ctx["final_zip"].exists() and bool(ctx["screenshots"])
    score += add_check(findings, case, "confidence_delivery", confidence_ok, "final bundle and screenshots", "Final package or screenshots are missing.")
    plain_ok = bool(ctx["readme"]) and ("README" in ctx["final_zip_tree"] or any(name.endswith("README.md") for name in ctx["final_zip_tree"]))
    score += add_check(findings, case, "plain_language", plain_ok, "README in package", "Customer-facing README is not visible in package tree.")
    positives = [
        "Run freezes to a team task-management product instead of a generic scaffold." if spec_domain_ok(ctx) else "",
        f"Customer can inspect {len(ctx['screenshots'])} screenshot artifact(s)." if ctx["screenshots"] else "",
        "Final project bundle exists." if ctx["final_zip"].exists() else "",
    ]
    issues = [
        finding["issue"] for finding in findings if not finding["passed"] and finding.get("issue")
    ]
    if ctx["run"].get("dirty") is True:
        issues.append("Run metadata reports dirty=true; this is not a benchmark blocker, but a customer may ask which repo changes were included.")
    return {
        "agent_id": "customer_agent",
        "score": score,
        "max_score": 25,
        "verdict": "satisfied" if score >= 20 else ("mixed" if score >= 15 else "unsatisfied"),
        "findings": findings,
        "positives": [item for item in positives if item],
        "issues": issues,
        "inputs_used": ["benchmark case", "transcript/support inbox", "README", "screenshots", "final bundle"],
        "benchmark_goal": benchmark_case.get("goal", ""),
    }


def product_agent(ctx: dict[str, Any]) -> dict[str, Any]:
    case = load_case("product_review_checklist.json")
    findings: list[dict[str, Any]] = []
    score = 0
    docs = ctx["docs"]
    ledger = ctx["extended_ledger"]
    page_count = len(ledger.get("implemented_pages", [])) if ledger else len(ctx["screenshots"])
    capability_text = " ".join([docs.get("feature_matrix", ""), ctx["readme"], " ".join(ctx["final_zip_tree"])])
    score += add_check(findings, case, "domain_freeze", spec_domain_ok(ctx), "project_spec/output_contract_freeze", "Product is not frozen as team_task_pm_web.")
    required_pages = 8 if is_hq(ctx) else 3
    score += add_check(findings, case, "page_depth", page_count >= required_pages, f"page_count={page_count}, required={required_pages}", "Page depth is below benchmark tier.")
    capability_ok = all(token in capability_text.lower() for token in ("task", "board")) and any(token in capability_text.lower() for token in ("search", "filter", "label"))
    score += add_check(findings, case, "feature_depth", capability_ok, "feature matrix/README/package tree", "Task board/list/search/filter capability evidence is thin or missing.")
    data_ok = bool(docs.get("data_model_summary")) or any("models.py" in name for name in ctx["final_zip_tree"])
    score += add_check(findings, case, "data_model", data_ok, "data model summary or models.py", "Data model summary/source model evidence is missing.")
    non_generic = spec_domain_ok(ctx) and any("task" in name.lower() or "kanban" in name.lower() or "dashboard" in name.lower() for name in ctx["final_zip_tree"] + ctx["screenshots"])
    score += add_check(findings, case, "non_generic_product", non_generic, "package tree/screenshots", "Package still looks generic.")
    issues = [finding["issue"] for finding in findings if not finding["passed"] and finding.get("issue")]
    if is_hq(ctx) and len(ctx["screenshots"]) >= 8:
        positives = ["High-quality profile has at least eight screenshots.", "Extended page/capability ledger is present." if ledger else ""]
    else:
        positives = ["Basic Plane-lite product shape is represented." if spec_domain_ok(ctx) else ""]
    return {
        "agent_id": "product_reviewer_agent",
        "score": score,
        "max_score": 25,
        "verdict": "tier_fit" if score >= 20 else ("quality_risk" if score >= 15 else "not_fit"),
        "findings": findings,
        "positives": [item for item in positives if item],
        "issues": issues,
        "inputs_used": ["project_spec", "output_contract_freeze", "docs", "screenshots", "final package tree"],
    }


def qa_agent(ctx: dict[str, Any]) -> dict[str, Any]:
    case = load_case("qa_checklist.json")
    findings: list[dict[str, Any]] = []
    score = 0
    acceptance = ctx["acceptance"]
    api_ok = [row for row in ctx["api_rows"] if str(row.get("status", "")).upper() == "OK"]
    api_err = [row for row in ctx["api_rows"] if str(row.get("status", "")).upper() == "ERR"]
    gate = ctx["support_delivery"].get("completion_gate", {}) if isinstance(ctx["support_delivery"].get("completion_gate"), dict) else {}
    score += add_check(findings, case, "acceptance_triplets", bool(acceptance["triplet_dirs"]) and not acceptance["missing_triplets"], f"triplets={len(acceptance['triplet_dirs'])}, ledger_lines={acceptance['ledger_lines']}", "Acceptance triplets or ledger are incomplete.")
    score += add_check(findings, case, "fallback_integrity", not acceptance["fallback_passed"], f"fallback_passed={acceptance['fallback_passed']}", "Fallback was accepted as passed.")
    score += add_check(findings, case, "api_truth", bool(api_ok), f"api_ok={len(api_ok)}, api_err={len(api_err)}", "No successful remote API call is visible.")
    score += add_check(findings, case, "verify_truth", ctx["verify"].get("result") == "PASS", "verify_report.json", "Verify report is missing or not PASS.")
    delivery_ok = bool(gate.get("passed")) and bool(gate.get("cold_replay_passed"))
    score += add_check(findings, case, "delivery_truth", delivery_ok, "support_public_delivery completion_gate", "Delivery gate or cold replay failed.")
    blockers = []
    if acceptance["fallback_passed"]:
        blockers.append("fallback accepted as passed")
    if ctx["verify"].get("result") != "PASS":
        blockers.append("verify did not pass")
    if not delivery_ok:
        blockers.append("delivery/cold replay did not pass")
    suspicious = ""
    if api_err:
        suspicious = f"{len(api_err)} API error row(s) are present; acceptable only if retried and not accepted via fallback."
    elif ctx["run"].get("dirty") is True:
        suspicious = "RUN.json has dirty=true; audit context should keep repo-level verify separate."
    return {
        "agent_id": "qa_adversarial_agent",
        "score": score,
        "max_score": 25,
        "verdict": "no_blocker" if not blockers and score >= 20 else ("watch" if not blockers else "blocker"),
        "findings": findings,
        "positives": ["Acceptance triplets and ledger are present." if acceptance["triplet_dirs"] else "", "Remote API calls are visible." if api_ok else ""],
        "issues": blockers + ([suspicious] if suspicious else []),
        "blockers": blockers,
        "first_suspicious_point": suspicious,
        "inputs_used": ["acceptance", "step_meta", "events", "api_calls", "verify", "delivery/replay"],
    }


def delivery_agent(ctx: dict[str, Any]) -> dict[str, Any]:
    case = load_case("delivery_checklist.json")
    findings: list[dict[str, Any]] = []
    score = 0
    final_tree = ctx["final_zip_tree"]
    evidence_tree = ctx["evidence_zip_tree"]
    support = ctx["support_delivery"]
    sent = support.get("sent", []) if isinstance(support.get("sent"), list) else []
    sent_photos = [item for item in sent if isinstance(item, dict) and item.get("type") == "photo"]
    package_ok = ctx["final_zip"].exists() and any(name.endswith("scripts/run_project_web.py") or name.endswith("app.py") for name in final_tree)
    score += add_check(findings, case, "package_portability", package_ok, "final_project_bundle tree", "Final package lacks a detectable runnable entrypoint.")
    startup_ok = bool(ctx["readme"]) and any(token in ctx["readme"].lower() for token in ("startup", "启动", "run_project", "python"))
    score += add_check(findings, case, "startup_clarity", startup_ok, "README/startup text", "Startup steps are unclear or missing.")
    visual_required = 8 if is_hq(ctx) else 1
    visual_ok = len(ctx["screenshots"]) >= visual_required
    score += add_check(findings, case, "visual_review", visual_ok, f"screenshots={len(ctx['screenshots'])}, required={visual_required}", "Screenshot coverage is below profile requirement.")
    evidence_ok = ctx["evidence_zip"].exists() and any("project_spec.json" in name for name in evidence_tree) and any("review" in name.lower() for name in evidence_tree)
    score += add_check(findings, case, "evidence_bundle", evidence_ok, "intermediate_evidence_bundle tree", "Evidence bundle does not contain the expected audit chain.")
    handoff_ok = bool(support.get("completion_gate", {}).get("passed")) and ctx["final_zip"].exists()
    score += add_check(findings, case, "human_handoff", handoff_ok, "support_public_delivery.json", "Delivery manifest does not show a completed handoff.")
    issues = [finding["issue"] for finding in findings if not finding["passed"] and finding.get("issue")]
    if is_hq(ctx) and len(sent_photos) < len(ctx["screenshots"]):
        issues.append(f"Public delivery sent {len(sent_photos)} screenshot(s), while {len(ctx['screenshots'])} exist in the project/evidence bundle; acceptable but less convenient for human review.")
    return {
        "agent_id": "delivery_critic_agent",
        "score": score,
        "max_score": 25,
        "verdict": "deliverable" if score >= 20 and package_ok else ("handoff_risk" if score >= 15 else "not_deliverable"),
        "findings": findings,
        "positives": ["Final project bundle exists and has an entrypoint." if package_ok else "", "Intermediate evidence bundle exists." if ctx["evidence_zip"].exists() else ""],
        "issues": issues,
        "deliverable": score >= 20 and package_ok,
        "inputs_used": ["final zip tree", "evidence zip tree", "README", "screenshots", "delivery manifests"],
    }


def markdown_report(title: str, result: dict[str, Any]) -> str:
    lines = [f"# {title}", "", f"- Score: `{result['score']}/25`", f"- Verdict: `{result['verdict']}`", ""]
    lines.append("## Inputs Used")
    for item in result.get("inputs_used", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Positives")
    positives = result.get("positives", []) or ["None recorded."]
    for item in positives:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Issues")
    issues = result.get("issues", []) or ["No role-level issue found."]
    for item in issues:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Checklist")
    for finding in result.get("findings", []):
        status = "PASS" if finding.get("passed") else "FAIL"
        lines.append(f"- `{status}` {finding.get('id')}: {finding.get('awarded')}/{finding.get('points')} - {finding.get('evidence')}")
        if finding.get("issue") and not finding.get("passed"):
            lines.append(f"  - Issue: {finding.get('issue')}")
    return "\n".join(lines) + "\n"


def benchmark_hard_gate_passed(ctx: dict[str, Any]) -> bool:
    gate = ctx["support_delivery"].get("completion_gate", {}) if isinstance(ctx["support_delivery"].get("completion_gate"), dict) else {}
    find_decision = ctx["find_result"].get("decision", {}) if isinstance(ctx["find_result"].get("decision"), dict) else {}
    return (
        ctx["run"].get("status") == "pass"
        and ctx["find_result"].get("selected_workflow_id") == "wf_project_generation_manifest"
        and bool(find_decision.get("project_generation_goal"))
        and spec_domain_ok(ctx)
        and ctx["verify"].get("result") == "PASS"
        and bool(gate.get("passed"))
        and bool(gate.get("cold_replay_passed"))
        and ctx["final_zip"].exists()
        and ctx["evidence_zip"].exists()
    )


def overall_verdict(ctx: dict[str, Any], results: list[dict[str, Any]]) -> tuple[str, str]:
    total = sum(int(item.get("score", 0) or 0) for item in results)
    qa = next(item for item in results if item["agent_id"] == "qa_adversarial_agent")
    delivery = next(item for item in results if item["agent_id"] == "delivery_critic_agent")
    if not benchmark_hard_gate_passed(ctx):
        return "FAIL", "benchmark hard gate did not pass"
    if qa.get("blockers"):
        return "FAIL", "QA found blocker: " + "; ".join(qa.get("blockers", []))
    if not delivery.get("deliverable"):
        return "FAIL", "Delivery Critic judged the project not deliverable"
    if total < 60:
        return "FAIL", "total score below 60"
    if total >= 80:
        return "PASS", ""
    return "PARTIAL", "total score between 60 and 79 or quality concerns remain"


def write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Agent League Summary",
        "",
        f"- Run dir: `{summary['run_dir']}`",
        f"- Benchmark hard gate passed: `{summary['benchmark_hard_gate_passed']}`",
        f"- Total score: `{summary['total_score']}/100`",
        f"- Verdict: `{summary['verdict']}`",
        f"- First failure point: `{summary.get('first_failure_point', '')}`",
        "",
        "## Role Results",
    ]
    for item in summary["agents"]:
        lines.append(f"- {item['agent_id']}: `{item['score']}/25`, verdict `{item['verdict']}`")
    lines.append("")
    lines.append("## Key Positives")
    for item in summary.get("key_positives", []) or ["None recorded."]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Key Issues")
    for item in summary.get("key_issues", []) or ["No league-level issue found."]:
        lines.append(f"- {item}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_league(run_dir: Path, benchmark_zip: Path, out_dir: Path) -> dict[str, Any]:
    ctx = collect_context(run_dir, benchmark_zip)
    out_dir.mkdir(parents=True, exist_ok=True)
    ordered = [
        ("customer_review.md", "Customer Agent Review", customer_agent(ctx)),
        ("product_review.md", "Product Reviewer Agent Review", product_agent(ctx)),
        ("qa_findings.md", "QA / Adversarial Agent Findings", qa_agent(ctx)),
        ("delivery_review.md", "Delivery Critic Review", delivery_agent(ctx)),
    ]
    for filename, title, result in ordered:
        (out_dir / filename).write_text(markdown_report(title, result), encoding="utf-8")
    results = [item[2] for item in ordered]
    verdict, first_failure = overall_verdict(ctx, results)
    total = sum(int(item.get("score", 0) or 0) for item in results)
    positives: list[str] = []
    issues: list[str] = []
    for result in results:
        positives.extend([str(item) for item in result.get("positives", []) if item])
        issues.extend([str(item) for item in result.get("issues", []) if item])
    summary = {
        "schema_version": "ctcp-agent-league-summary-v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "run_dir": str(run_dir),
        "benchmark_zip": str(benchmark_zip),
        "benchmark_hard_gate_passed": benchmark_hard_gate_passed(ctx),
        "total_score": total,
        "verdict": verdict,
        "first_failure_point": first_failure,
        "agents": [
            {
                "agent_id": result["agent_id"],
                "score": result["score"],
                "max_score": result["max_score"],
                "verdict": result["verdict"],
                "report": filename,
                "issues": result.get("issues", []),
                "positives": result.get("positives", []),
            }
            for filename, _title, result in ordered
        ],
        "key_positives": positives[:8],
        "key_issues": issues[:8],
        "input_gaps": [
            "transcript missing or reconstructed" if not ctx["transcript_sources"] else "",
            "feature matrix missing" if is_hq(ctx) and not ctx["docs"].get("feature_matrix") else "",
            "page map missing" if is_hq(ctx) and not ctx["docs"].get("page_map") else "",
            "data model summary missing" if is_hq(ctx) and not ctx["docs"].get("data_model_summary") else "",
        ],
    }
    summary["input_gaps"] = [item for item in summary["input_gaps"] if item]
    write_json(out_dir / "agent_league_summary.json", summary)
    write_summary_md(out_dir / "agent_league_summary.md", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the CTCP Agent League on an existing benchmark run directory.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--benchmark-zip", type=Path, default=DEFAULT_BENCHMARK_ZIP)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args(argv)
    run_dir = args.run_dir.resolve()
    out_dir = args.out_dir.resolve() if args.out_dir else run_dir / "artifacts" / "agent_league"
    summary = run_league(run_dir, args.benchmark_zip.resolve(), out_dir)
    print(json.dumps({"summary": str(out_dir / "agent_league_summary.json"), "total_score": summary["total_score"], "verdict": summary["verdict"]}, ensure_ascii=False))
    return 0 if summary["verdict"] in {"PASS", "PARTIAL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
