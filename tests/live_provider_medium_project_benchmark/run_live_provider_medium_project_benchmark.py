from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TESTS_DIR = ROOT / "tests"
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

try:
    from tests.provider_assisted_benchmark import run_provider_assisted_benchmark as base
except ModuleNotFoundError:
    from provider_assisted_benchmark import run_provider_assisted_benchmark as base
from tools.providers.project_generation_medium_candidate import medium_project_contract


BENCH_DIR = Path(__file__).resolve().parent
FIXTURES = [
    BENCH_DIR / "fixtures" / "live_provider_inventory_manager_app.json",
    BENCH_DIR / "fixtures" / "live_provider_knowledge_base_app.json",
    BENCH_DIR / "fixtures" / "live_provider_event_booking_app.json",
    BENCH_DIR / "fixtures" / "live_provider_invoice_manager_app.json",
]
GENERATED = BENCH_DIR / "generated"
SUMMARY_PATH = GENERATED / "live_provider_medium_project_summary.json"
REPORT_PATH = BENCH_DIR / "benchmark_report.md"
REVIEW_PACK_PATH = ROOT / "meta" / "reports" / "REVIEW_PACK.md"
BLIND_SUMMARY = ROOT / "tests" / "live_provider_blind_matrix" / "generated" / "live_provider_blind_matrix_summary.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _phase20_gate() -> dict[str, Any]:
    if not BLIND_SUMMARY.exists():
        return {"phase20_gate_passed": False, "reason": "blind_matrix_summary_missing"}
    doc = _read_json(BLIND_SUMMARY)
    passed = bool(
        doc.get("phase20_gate_passed") is True
        and int(doc.get("accepted_count", 0) or 0) >= 2
        and int(doc.get("accepted_count", 0) or 0) + int(doc.get("repaired_count", 0) or 0) >= 4
        and int(doc.get("fallback_count", 0) or 0) <= 1
        and int(doc.get("failed_count", 0) or 0) == 0
    )
    out = dict(doc)
    out["phase20_gate_passed"] = passed
    if not passed:
        out["reason"] = "phase20_gate_not_passed"
    return out


def _env() -> dict[str, str]:
    env = base._env()
    env["CTCP_RUNS_ROOT"] = str((Path(tempfile.gettempdir()) / "ctcp_live_provider_medium_project_runs").resolve())
    env["CTCP_LIVE_MEDIUM_CANDIDATE"] = "1"
    env["CTCP_LIVE_FULL_CANDIDATE_ATTEMPTS"] = str(os.environ.get("CTCP_LIVE_FULL_CANDIDATE_ATTEMPTS", "3"))
    env["CTCP_LIVE_FULL_CANDIDATE_MAX_OUTPUT_TOKENS"] = str(os.environ.get("CTCP_LIVE_FULL_CANDIDATE_MAX_OUTPUT_TOKENS", "7000"))
    env["CTCP_LIVE_FULL_CANDIDATE_TIMEOUT_SEC"] = str(os.environ.get("CTCP_LIVE_FULL_CANDIDATE_TIMEOUT_SEC", "120"))
    env.pop("CTCP_PROVIDER_ASSISTED", None)
    env.pop("CTCP_PROVIDER_ASSISTED_FIXTURE", None)
    env.pop("CTCP_LIVE_PROVIDER_ASSISTED", None)
    env.pop("CTCP_LIVE_FULL_CANDIDATE_FORCE_INVALID", None)
    return env


def _generated_tests(project_dir: Path) -> dict[str, Any]:
    return base._run([sys.executable, "-m", "unittest", "discover", "-v"], env=base._test_env(project_dir), cwd=project_dir, timeout=120)


def _start_server(project_dir: Path, port: int) -> subprocess.Popen:
    env = base._test_env(project_dir)
    return subprocess.Popen(
        [sys.executable, "app.py", "--host", "127.0.0.1", "--port", str(port)],
        cwd=project_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _stop_server(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def _wait_http(base_url: str, proc: subprocess.Popen) -> bool:
    for _ in range(40):
        if proc.poll() is not None:
            return False
        try:
            base._http_text(base_url + "/")
            return True
        except Exception:
            time.sleep(0.2)
    return False


def _validate_inventory(project_dir: Path) -> dict[str, Any]:
    try:
        return _validate_inventory_impl(project_dir)
    except Exception as exc:
        return {"passed": False, "error": repr(exc)}


def _validate_inventory_impl(project_dir: Path) -> dict[str, Any]:
    for db in project_dir.glob("*.db"):
        db.unlink()
    port = base._free_port()
    proc = _start_server(project_dir, port)
    url = f"http://127.0.0.1:{port}"
    try:
        ready = _wait_http(url, proc)
        html = base._http_text(url + "/") if ready else ""
        js = (project_dir / "static" / "app.js").read_text(encoding="utf-8") if (project_dir / "static" / "app.js").exists() else ""
        status, product = base._http_json("POST", url + "/products", {"sku": "SKU1", "name": "Widget", "quantity": 2, "reorder_level": 3})
        product_id = int(product.get("id", 0) or 0)
        list_status, listed = base._http_json("GET", url + "/products")
        get_status, got = base._http_json("GET", url + f"/products/{product_id}")
        patch_status, patched = base._http_json("PATCH", url + f"/products/{product_id}", {"name": "Widget Plus"})
        adjust_status, adjusted = base._http_json("POST", url + f"/products/{product_id}/adjust", {"delta": 5, "reason": "received"})
        low_status, low = base._http_json("GET", url + "/low-stock")
        moves_status, moves = base._http_json("GET", url + "/movements")
        delete_status, deleted = base._http_json("DELETE", url + f"/products/{product_id}")
    finally:
        _stop_server(proc)
    port2 = base._free_port()
    proc2 = _start_server(project_dir, port2)
    url2 = f"http://127.0.0.1:{port2}"
    try:
        restart_ready = _wait_http(url2, proc2)
        restart_status, restart_list = base._http_json("GET", url2 + "/products") if restart_ready else (0, {})
    finally:
        _stop_server(proc2)
    passed = bool(
        ready
        and "Inventory" in html
        and "fetch(" in js
        and status == 201
        and product_id > 0
        and list_status == 200
        and get_status == 200
        and patch_status == 200
        and patched.get("name") == "Widget Plus"
        and adjust_status == 200
        and int(adjusted.get("quantity", -1)) == 7
        and low_status == 200
        and moves_status == 200
        and len(moves.get("movements", [])) >= 1
        and delete_status == 200
        and deleted.get("deleted") is True
        and restart_status == 200
        and isinstance(restart_list.get("products"), list)
    )
    return {"passed": passed, "frontend_served": "Inventory" in html, "js_fetch": "fetch(" in js, "restart_status": restart_status}


def _validate_kb(project_dir: Path) -> dict[str, Any]:
    try:
        return _validate_kb_impl(project_dir)
    except Exception as exc:
        return {"passed": False, "error": repr(exc)}


def _validate_kb_impl(project_dir: Path) -> dict[str, Any]:
    for db in project_dir.glob("*.db"):
        db.unlink()
    port = base._free_port()
    proc = _start_server(project_dir, port)
    url = f"http://127.0.0.1:{port}"
    try:
        ready = _wait_http(url, proc)
        html = base._http_text(url + "/") if ready else ""
        js = (project_dir / "static" / "app.js").read_text(encoding="utf-8") if (project_dir / "static" / "app.js").exists() else ""
        status, article = base._http_json("POST", url + "/articles", {"title": "Install Guide", "body": "Use local Python", "tags": ["docs", "python"]})
        article_id = int(article.get("id", 0) or 0)
        list_status, listed = base._http_json("GET", url + "/articles")
        get_status, got = base._http_json("GET", url + f"/articles/{article_id}")
        patch_status, patched = base._http_json("PATCH", url + f"/articles/{article_id}", {"body": "Updated", "tags": ["docs"]})
        search_status, search = base._http_json("GET", url + "/search?q=Updated")
        tags_status, tags = base._http_json("GET", url + "/tags")
        delete_status, deleted = base._http_json("DELETE", url + f"/articles/{article_id}")
    finally:
        _stop_server(proc)
    port2 = base._free_port()
    proc2 = _start_server(project_dir, port2)
    url2 = f"http://127.0.0.1:{port2}"
    try:
        restart_ready = _wait_http(url2, proc2)
        restart_status, restart_list = base._http_json("GET", url2 + "/articles") if restart_ready else (0, {})
    finally:
        _stop_server(proc2)
    passed = bool(
        ready
        and "Knowledge" in html
        and "fetch(" in js
        and status == 201
        and article_id > 0
        and list_status == 200
        and get_status == 200
        and patch_status == 200
        and patched.get("body") == "Updated"
        and search_status == 200
        and len(search.get("articles", [])) >= 1
        and tags_status == 200
        and "docs" in tags.get("tags", [])
        and delete_status == 200
        and deleted.get("deleted") is True
        and restart_status == 200
        and isinstance(restart_list.get("articles"), list)
    )
    return {"passed": passed, "frontend_served": "Knowledge" in html, "js_fetch": "fetch(" in js, "restart_status": restart_status}


def _validate_event(project_dir: Path) -> dict[str, Any]:
    try:
        return _validate_event_impl(project_dir)
    except Exception as exc:
        return {"passed": False, "error": repr(exc)}


def _validate_event_impl(project_dir: Path) -> dict[str, Any]:
    for db in project_dir.glob("*.db"):
        db.unlink()
    port = base._free_port()
    proc = _start_server(project_dir, port)
    url = f"http://127.0.0.1:{port}"
    try:
        ready = _wait_http(url, proc)
        html = base._http_text(url + "/") if ready else ""
        js = (project_dir / "static" / "app.js").read_text(encoding="utf-8") if (project_dir / "static" / "app.js").exists() else ""
        status, event = base._http_json("POST", url + "/events", {"title": "Demo Day", "date": "2026-06-01", "capacity": 1})
        event_id = int(event.get("id", 0) or 0)
        list_status, listed = base._http_json("GET", url + "/events")
        get_status, got = base._http_json("GET", url + f"/events/{event_id}")
        patch_status, patched = base._http_json("PATCH", url + f"/events/{event_id}", {"title": "Demo Night"})
        book_status, booking = base._http_json("POST", url + f"/events/{event_id}/bookings", {"attendee_name": "A", "attendee_email": "a@example.test"})
        over_status, over = base._http_json("POST", url + f"/events/{event_id}/bookings", {"attendee_name": "B", "attendee_email": "b@example.test"})
        bookings_status, bookings = base._http_json("GET", url + f"/events/{event_id}/bookings")
        availability_status, availability = base._http_json("GET", url + "/availability")
        delete_status, deleted = base._http_json("DELETE", url + f"/events/{event_id}")
    finally:
        _stop_server(proc)
    port2 = base._free_port()
    proc2 = _start_server(project_dir, port2)
    url2 = f"http://127.0.0.1:{port2}"
    try:
        restart_ready = _wait_http(url2, proc2)
        restart_status, restart_list = base._http_json("GET", url2 + "/events") if restart_ready else (0, {})
    finally:
        _stop_server(proc2)
    passed = bool(
        ready
        and "Event" in html
        and "fetch(" in js
        and status == 201
        and event_id > 0
        and list_status == 200
        and get_status == 200
        and patch_status == 200
        and patched.get("title") == "Demo Night"
        and book_status == 201
        and booking.get("event_id") == event_id
        and over_status == 409
        and bookings_status == 200
        and len(bookings.get("bookings", [])) == 1
        and availability_status == 200
        and availability.get("availability", [{}])[0].get("remaining") == 0
        and delete_status == 200
        and deleted.get("deleted") is True
        and restart_status == 200
        and isinstance(restart_list.get("events"), list)
    )
    return {"passed": passed, "frontend_served": "Event" in html, "js_fetch": "fetch(" in js, "restart_status": restart_status}


def _validate_invoice(project_dir: Path) -> dict[str, Any]:
    try:
        return _validate_invoice_impl(project_dir)
    except Exception as exc:
        return {"passed": False, "error": repr(exc)}


def _validate_invoice_impl(project_dir: Path) -> dict[str, Any]:
    for db in project_dir.glob("*.db"):
        db.unlink()
    port = base._free_port()
    proc = _start_server(project_dir, port)
    url = f"http://127.0.0.1:{port}"
    try:
        ready = _wait_http(url, proc)
        html = base._http_text(url + "/") if ready else ""
        js = (project_dir / "static" / "app.js").read_text(encoding="utf-8") if (project_dir / "static" / "app.js").exists() else ""
        client_status, client = base._http_json("POST", url + "/clients", {"name": "Acme", "email": "a@example.test"})
        client_id = int(client.get("id", 0) or 0)
        clients_status, clients = base._http_json("GET", url + "/clients")
        invoice_status, invoice = base._http_json("POST", url + "/invoices", {"client_id": client_id, "number": "INV-1"})
        invoice_id = int(invoice.get("id", 0) or 0)
        invoices_status, invoices = base._http_json("GET", url + "/invoices")
        get_status, got = base._http_json("GET", url + f"/invoices/{invoice_id}")
        item_status, with_item = base._http_json("POST", url + f"/invoices/{invoice_id}/items", {"description": "Work", "quantity": 2, "unit_price": 50})
        status_status, sent = base._http_json("PATCH", url + f"/invoices/{invoice_id}/status", {"status": "sent"})
        summary_status, summary = base._http_json("GET", url + "/summary")
    finally:
        _stop_server(proc)
    port2 = base._free_port()
    proc2 = _start_server(project_dir, port2)
    url2 = f"http://127.0.0.1:{port2}"
    try:
        restart_ready = _wait_http(url2, proc2)
        restart_status, restart_list = base._http_json("GET", url2 + "/invoices") if restart_ready else (0, {})
    finally:
        _stop_server(proc2)
    passed = bool(
        ready
        and "Invoice" in html
        and "fetch(" in js
        and client_status == 201
        and client_id > 0
        and clients_status == 200
        and len(clients.get("clients", [])) >= 1
        and invoice_status == 201
        and invoice_id > 0
        and invoices_status == 200
        and get_status == 200
        and item_status == 200
        and float(with_item.get("total", 0.0)) == 110.0
        and status_status == 200
        and sent.get("status") == "sent"
        and summary_status == 200
        and int(summary.get("invoice_count", 0)) >= 1
        and restart_status == 200
        and isinstance(restart_list.get("invoices"), list)
    )
    return {"passed": passed, "frontend_served": "Invoice" in html, "js_fetch": "fetch(" in js, "restart_status": restart_status}


VALIDATORS = {
    "live_provider_inventory_manager_app": _validate_inventory,
    "live_provider_knowledge_base_app": _validate_kb,
    "live_provider_event_booking_app": _validate_event,
    "live_provider_invoice_manager_app": _validate_invoice,
}


def _validate_project(fixture: dict[str, Any], run_dir: Path, commands: list[dict[str, Any]]) -> dict[str, Any]:
    project = str(fixture["project"])
    project_dir = run_dir / "project_output" / project
    attribution_path = run_dir / "artifacts" / "generation_attribution.json"
    attribution = _read_json(attribution_path) if attribution_path.exists() else {}
    tests = _generated_tests(project_dir) if project_dir.exists() else {"exit_code": 1, "stdout": "", "stderr": "missing_project_dir"}
    runtime = VALIDATORS[project](project_dir) if project_dir.exists() else {"passed": False, "reason": "missing_project_dir"}
    command_text = "\n".join(str(row.get("cmd", "")) for row in commands)
    ordinary_mainline = all(token in command_text for token in ("new-run", "status", "advance"))
    no_agent_scaffold = not (project_dir / "run_agent.py").exists() and not (project_dir / "runtime").exists()
    outcome = str(attribution.get("provider_candidate_outcome", "failed") or "failed")
    ratio = float(attribution.get("provider_authored_file_ratio", 0.0) or 0.0)
    contract_rel = str(attribution.get("medium_project_contract_path", ""))
    contract_path = run_dir / contract_rel if contract_rel else run_dir / "missing_medium_project_contract.json"
    expected_contract = medium_project_contract(project)
    contract = _read_json(contract_path) if contract_path.exists() else {}
    contract_ok = bool(
        contract_path.exists()
        and contract.get("case_name") == project
        and set(expected_contract["required_files"]).issubset(set(contract.get("required_files", [])))
        and set(expected_contract["routes"]).issubset(set(contract.get("routes", [])))
    )
    attribution_ok = bool(
        attribution.get("generation_mode") == "live_provider_medium_candidate"
        and attribution.get("medium_case") is True
        and attribution.get("medium_case_name") == project
        and attribution.get("used_agent_project") is False
        and attribution.get("used_agent_scaffold") is False
        and attribution.get("used_local_agent_runtime") is False
        and attribution.get("used_provider_agent") is True
        and int(attribution.get("provider_request_count", 0) or 0) > 0
        and outcome in {"accepted", "repaired", "fallback", "unsupported"}
        and contract_rel == "artifacts/medium_project_contract.json"
        and contract_ok
    )
    if outcome in {"accepted", "repaired"}:
        attribution_ok = attribution_ok and ratio >= 0.6
    passed = bool(project_dir.exists() and no_agent_scaffold and ordinary_mainline and attribution_ok and tests["exit_code"] == 0 and runtime.get("passed") is True)
    return {
        "case": fixture["case"],
        "project": project,
        "status": "passed" if passed else "failed",
        "outcome": outcome,
        "project_dir": str(project_dir),
        "attribution_path": str(attribution_path),
        "attribution": attribution,
        "medium_project_contract_path": str(contract_path),
        "medium_project_contract_ok": contract_ok,
        "provider_authored_file_ratio": ratio,
        "generated_tests": tests,
        "runtime_validation": runtime,
        "ordinary_mainline": ordinary_mainline,
        "no_agent_scaffold": no_agent_scaffold,
    }


def _run_case(path: Path) -> dict[str, Any]:
    fixture = _read_json(path)
    project = str(fixture["project"])
    env = _env()
    commands: list[dict[str, Any]] = []
    run_id = f"medium-{project}-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    goal = str(fixture["goal"]) + " Use ordinary CTCP new-run/status/advance and source_generation; do not use agent scaffold."
    new_run = base._run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "new-run", "--goal", goal, "--run-id", run_id], env=env, timeout=180)
    commands.append(new_run)
    if new_run["exit_code"] != 0:
        return {"case": fixture["case"], "project": project, "status": "failed", "commands": commands, "reason": "new_run_failed"}
    run_dir = base._run_dir_from_output(new_run)
    base._force_local_dispatch(run_dir)
    commands.append(base._run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)], env=env, timeout=90))
    for _ in range(28):
        commands.append(base._run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "advance", "--run-dir", str(run_dir), "--max-steps", "1"], env=env, timeout=480))
        if (run_dir / "artifacts" / "source_generation_report.json").exists() and (run_dir / "project_output" / project / "app.py").exists():
            break
    commands.append(base._run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)], env=env, timeout=90))
    result = _validate_project(fixture, run_dir, commands)
    result["commands"] = commands
    result["run_dir"] = str(run_dir)
    return result


def _write_report(summary: dict[str, Any]) -> None:
    lines = [
        "# Live Provider Medium Project Benchmark",
        "",
        "## Summary",
        f"- status: `{summary['status']}`",
        f"- case_count: `{summary['case_count']}`",
        f"- accepted_count: `{summary['accepted_count']}`",
        f"- repaired_count: `{summary['repaired_count']}`",
        f"- fallback_count: `{summary['fallback_count']}`",
        f"- failed_count: `{summary['failed_count']}`",
        f"- provider_request_count: `{summary['provider_request_count']}`",
        f"- provider_plan_valid_count: `{summary.get('provider_plan_valid_count')}`",
        f"- provider_manifest_valid_count: `{summary.get('provider_manifest_valid_count')}`",
        f"- provider_batch_count: `{summary.get('provider_batch_count')}`",
        f"- provider_project_candidate_count: `{summary['provider_project_candidate_count']}`",
        "",
        "## Cases",
        "| case | plan_valid | manifest_valid | batch_count | candidate_count | outcome | repair_attempts | fallback_reason | provider_authored_file_ratio |",
        "|---|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for row in summary["cases"]:
        attr = row.get("attribution", {})
        lines.append(
            f"| `{row.get('project')}` | `{attr.get('provider_plan_valid')}` | `{attr.get('provider_manifest_valid')}` | "
            f"`{attr.get('provider_batch_count')}` | `{attr.get('provider_project_candidate_count')}` | "
            f"`{row.get('outcome')}` | `{attr.get('provider_repair_attempt_count')}` | "
            f"`{attr.get('fallback_reason', '')}` | `{row.get('provider_authored_file_ratio')}` |"
        )
    lines.extend(["", "## Diagnostics"])
    for row in summary["cases"]:
        attr = row.get("attribution", {})
        lines.append(f"- `{row.get('project')}` raw responses: `{', '.join(attr.get('provider_raw_response_paths', []))}`")
        lines.append(f"- `{row.get('project')}` normalized manifest: `{attr.get('normalized_manifest_path', '')}`")
        lines.append(f"- `{row.get('project')}` medium project contract: `{row.get('medium_project_contract_path', '')}`")
        lines.append(f"- `{row.get('project')}` validation failures: `{attr.get('validation_failure_path', '')}`")
        lines.append(f"- `{row.get('project')}` repair report: `{attr.get('repair_report_path', '')}`")
        lines.append(f"- `{row.get('project')}` attribution: `{row.get('attribution_path')}`")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_medium_review_pack(summary: dict[str, Any], phase20: dict[str, Any]) -> None:
    existing = REVIEW_PACK_PATH.read_text(encoding="utf-8", errors="replace") if REVIEW_PACK_PATH.exists() else "# CTCP Review Pack\n"
    keep = existing.split("## Phase 20 Acceptance Hardening Summary", 1)[0].rstrip()
    lines = [
        keep,
        "",
        "## Phase 20 Acceptance Hardening Summary",
        "",
        "- previous accepted/repaired/fallback counts: `0/3/2`",
        f"- new accepted/repaired/fallback counts: `{phase20.get('accepted_count')}/{phase20.get('repaired_count')}/{phase20.get('fallback_count')}`",
        f"- acceptance_rate: `{phase20.get('acceptance_rate')}`",
        f"- accepted_or_repaired_rate: `{phase20.get('accepted_or_repaired_rate')}`",
        f"- gate passed: `{phase20.get('phase20_gate_passed')}`",
        "- changed logic: provider prompt contract, self-check requirements, manifest normalization, and strict gate metrics.",
        "- fixture lowering: `no`",
        "",
        "## Phase 22 Medium Success Expansion Summary",
        "",
        "- previous Phase 21B result: `2 cases, repaired=1, fallback=1, provider_medium_success=true`",
        f"- new case_count: `{summary.get('case_count')}`",
        f"- provider request count: `{summary.get('provider_request_count')}`",
        f"- provider plan valid count: `{summary.get('provider_plan_valid_count')}`",
        f"- provider manifest valid count: `{summary.get('provider_manifest_valid_count')}`",
        f"- provider batch count: `{summary.get('provider_batch_count')}`",
        f"- provider project candidate count: `{summary.get('provider_project_candidate_count')}`",
        f"- accepted count: `{summary.get('accepted_count')}`",
        f"- repaired count: `{summary.get('repaired_count')}`",
        f"- fallback count: `{summary.get('fallback_count')}`",
        f"- failed count: `{summary.get('failed_count')}`",
        f"- medium expansion gate passed: `{summary.get('status') == 'passed'}`",
        "- ordinary mainline: `new-run/status/advance`",
        "- agent-project/scaffold substitution: `no`",
        "- contract validation: `medium_project_contract.json` required for every case",
        "",
        "| Case | Outcome | Provider Authored File Ratio | Contract | Runtime |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in summary.get("cases", []):
        lines.append(f"| `{row.get('project')}` | `{row.get('outcome')}` | `{row.get('provider_authored_file_ratio')}` | `{row.get('medium_project_contract_ok')}` | `{row.get('runtime_validation', {}).get('passed')}` |")
    lines.extend([
        "",
        "## Reproduction Commands",
        "- `.\\.venv\\Scripts\\python.exe tests\\live_provider_blind_matrix\\run_live_provider_blind_matrix.py`",
        "- `.\\.venv\\Scripts\\python.exe tests\\live_provider_medium_project_benchmark\\run_live_provider_medium_project_benchmark.py`",
        "",
        "## Risk Notes",
        "- Medium provider candidates are still gated by deterministic safety, generated tests, runtime validation, and attribution.",
        "- Fallback classifications remain allowed but do not count as provider medium success.",
    ])
    REVIEW_PACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PACK_PATH.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _blocked_summary(phase20: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": "phase20_gate_not_passed",
        "phase20": phase20,
        "case_count": 0,
        "accepted_count": 0,
        "repaired_count": 0,
        "fallback_count": 0,
        "unsupported_count": 0,
        "failed_count": 0,
        "provider_request_count": 0,
        "provider_project_candidate_count": 0,
        "cases": [],
        "summary": str(SUMMARY_PATH),
        "report": str(REPORT_PATH),
    }


def main() -> int:
    GENERATED.mkdir(parents=True, exist_ok=True)
    phase20 = _phase20_gate()
    if not phase20.get("phase20_gate_passed"):
        summary = _blocked_summary(phase20)
        _write_json(SUMMARY_PATH, summary)
        _write_report(summary)
        write_medium_review_pack(summary, phase20)
        print(json.dumps({k: summary[k] for k in ("status", "reason")}, indent=2))
        return 1
    cases = [_run_case(path) for path in FIXTURES]
    accepted = sum(1 for row in cases if row.get("outcome") == "accepted")
    repaired = sum(1 for row in cases if row.get("outcome") == "repaired")
    fallback = sum(1 for row in cases if row.get("outcome") == "fallback")
    unsupported = sum(1 for row in cases if row.get("outcome") == "unsupported")
    failed = sum(1 for row in cases if row.get("status") != "passed")
    request_count = sum(int(row.get("attribution", {}).get("provider_request_count", 0) or 0) for row in cases)
    candidate_count = sum(int(row.get("attribution", {}).get("provider_project_candidate_count", 0) or 0) for row in cases)
    plan_valid_count = sum(1 for row in cases if row.get("attribution", {}).get("provider_plan_valid") is True)
    manifest_valid_count = sum(1 for row in cases if row.get("attribution", {}).get("provider_manifest_valid") is True)
    batch_count = sum(int(row.get("attribution", {}).get("provider_batch_count", 0) or 0) for row in cases)
    medium_success = bool(accepted + repaired >= 2 and all(float(row.get("provider_authored_file_ratio", 0.0) or 0.0) >= 0.6 for row in cases if row.get("outcome") in {"accepted", "repaired"}))
    contracts_ok = all(row.get("medium_project_contract_ok") is True for row in cases)
    status = "passed" if len(cases) >= 4 and candidate_count >= len(cases) and fallback <= 1 and failed == 0 and medium_success and contracts_ok else "failed"
    summary = {
        "status": status,
        "case_count": len(cases),
        "accepted_count": accepted,
        "repaired_count": repaired,
        "fallback_count": fallback,
        "unsupported_count": unsupported,
        "failed_count": failed,
        "provider_request_count": request_count,
        "provider_plan_valid_count": plan_valid_count,
        "provider_manifest_valid_count": manifest_valid_count,
        "provider_batch_count": batch_count,
        "provider_project_candidate_count": candidate_count,
        "provider_medium_success": medium_success,
        "medium_project_contracts_ok": contracts_ok,
        "phase20": phase20,
        "cases": cases,
        "summary": str(SUMMARY_PATH),
        "report": str(REPORT_PATH),
        "review_pack": str(REVIEW_PACK_PATH),
    }
    _write_json(SUMMARY_PATH, summary)
    _write_report(summary)
    write_medium_review_pack(summary, phase20)
    print(json.dumps({k: summary[k] for k in ("status", "case_count", "accepted_count", "repaired_count", "fallback_count", "unsupported_count", "failed_count", "provider_request_count", "provider_plan_valid_count", "provider_manifest_valid_count", "provider_batch_count", "provider_project_candidate_count", "provider_medium_success")}, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
