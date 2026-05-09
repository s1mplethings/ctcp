from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _contract_snapshot(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "artifacts" / "output_contract_freeze.json"
    try:
        doc = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def render_source_generation_payload_requirements(*, run_dir: Path) -> list[str]:
    contract = _contract_snapshot(run_dir)
    project_root = str(contract.get("project_root", "project_output/app")).strip() or "project_output/app"
    startup_entrypoint = str(contract.get("startup_entrypoint", "")).strip().replace("\\", "/")
    project_domain = str(contract.get("project_domain", "")).strip()
    project_archetype = str(contract.get("project_archetype", "")).strip()
    delivery_shape = str(contract.get("delivery_shape", "")).strip()
    package_name = _package_name(contract=contract, project_root=project_root)
    entrypoint_name = startup_entrypoint.rsplit("/", 1)[-1] if startup_entrypoint else "the startup entrypoint"
    is_gui = delivery_shape == "gui_first" or entrypoint_name == "run_project_gui.py"
    is_web = delivery_shape == "web_first" or entrypoint_name == "run_project_web.py" or project_archetype == "web_service"
    is_narrative = (
        project_domain == "narrative_vn_editor"
        or "narrative" in project_archetype
        or package_name in {"vn", "narrative_copilot"}
        or project_root.rstrip("/").endswith("/vn")
    )
    required_paths = _expected_paths(contract=contract, project_root=project_root)
    required_lines = [f"- {item}" for item in required_paths[:80]] or [f"- {project_root}/README.md"]
    previous_failure_lines = _previous_failure_lines(run_dir)
    schema = '{"schema_version":"ctcp-provider-source-files-v1","files":[{"path":"project_output/<project_id>/README.md","content_lines":["# Project","startup text"]}],"source_map":{"api_content_applied":true,"api_content_source_ref":"API:api_agent/source_generation"}}'
    lines = [
        "## Source Generation Output Requirements",
        "Return one JSON object only. Do not return a generic project description.",
        "The JSON must include concrete project source files that can be written under the run directory and run locally.",
        "Required schema:",
        "```json",
        schema,
        "```",
        "File requirements:",
        f"- Every path must stay under `{project_root}`.",
        "- Treat this as a one-shot complete delivery bundle, not a partial draft. The first source_generation answer must include all runnable code, sample data, startup docs, UI/export evidence paths, and tests needed for validation.",
        "- Keep the MVP compact but complete: split responsibilities across the expected small files, avoid monolithic source files, and keep README/docs practical instead of long process essays.",
        "- Include every expected path listed below, including package __init__.py files, pyproject.toml, README, startup entrypoint, sample data, and tests.",
        "- Prefer `content_lines` as an array of complete source lines for every file; the system will join them with newline characters.",
        "- If you use `content` instead, it must be a complete file string with escaped `\\n`; never put literal line breaks inside a JSON string.",
        "- Treat source_generation as a virtual-team handoff, not a solo dump: Builder writes the files, Integration QA checks every import/export and call signature, Product QA checks the user-goal flow, and Delivery QA checks README commands, evidence files, and package layout before the JSON is returned.",
        "- If this is a retry, the Validator/QA failure evidence below is mandatory input. Do not repeat the same structure with only names changed; repair the concrete files, imports, constructors, routes, README headings, and tests that caused the failure.",
        "- The final JSON must reflect the integrated team decision: no file may contradict the package name, startup entrypoint, public interfaces, README commands, or tests chosen by another file.",
        "- The generated project is validated in the current Python environment. The verifier does not run `pip install`, `poetry install`, `npm install`, or any dependency bootstrap before startup/export probes.",
        "- Therefore every generated startup, export, test, and evidence path must run with Python standard library modules only unless the dependency code is included inside the generated project tree and imported locally.",
        "- For local HTTP/web projects, prefer standard-library `http.server`, `wsgiref`, `urllib`, `json`, `html`, and generated HTML/JavaScript assets; do not import Flask, flask_cors, FastAPI, Django, requests, PyQt5, PySide, wxPython, Electron, or other uninstalled packages.",
        "- `pyproject.toml` may document optional dependencies, but required validation paths must not import them. Optional dependency imports must be guarded and have a standard-library fallback.",
        "- The startup entrypoint must support `--help`, `--serve`, and `--goal --project-name --out --headless`; `--serve` and the rich export command must exit 0 under the verifier instead of blocking forever on a long-running server loop.",
        "- Do not add a custom argparse `--help` option; argparse already provides it. Only define real options such as `--goal`, `--project-name`, `--out`, and `--headless`.",
        f"- Prefer normal src-layout imports like `from {package_name}.service import ...`; do not import `src.{package_name}...` unless you also make it runnable with the project root on PYTHONPATH.",
        "- Inside a generated `src/<package>/...` package, do not use bare sibling imports such as `import service`, `import models`, or `from exporter import ...`. Use explicit relative imports like `from . import service` / `from .models import CommandWhitelist`, or absolute package imports like `from <package>.service import ...` consistently.",
        "- Entrypoint scripts under `scripts/` must add the generated `src` directory to `sys.path` when needed, then import the concrete package modules and symbols that actually exist. Do not rely on `__init__.py` re-exporting symbols that are not defined.",
        f"- Generated tests must run with `python -m unittest discover -s tests -v` using the generated `src` directory on PYTHONPATH. Tests must import the package directly, for example `from {package_name} import service` or `from {package_name}.service import VoiceAssistantService`; do not import `src.{package_name}`, `src.<package>`, or repo-local paths.",
        "- Before returning, build a cross-file import/export checklist: for every `from package.module import Symbol`, the target module must define `Symbol` or re-export it through its `__init__.py`.",
        "- Include an `interfaces` object in the JSON response, keyed by Python file path, listing each file's public `defines`, `imports`, and `exports`; this must match the actual file contents exactly.",
        "- In each `interfaces[path]`, include a `signatures` object for public classes/functions, for example `{ \"VoiceAssistantService\": \"VoiceAssistantService(whitelist)\", \"run_server\": \"run_server(port=..., service_inst=..., blocking=...)\" }`; every startup, route, exporter, and test call must match this matrix.",
        "- Package `__init__.py` files count as public code too: every `from .module import Symbol` or wildcard re-export in `__init__.py` must point to a real class/function/value in that module.",
        "- Do not import helper names that are not implemented. If one file imports a helper, the target file must define that exact helper or the importing file must call the actual implemented API.",
        "- Keep public function names consistent across service, entrypoint, exporter, pipeline, workspace, and tests; rename imports and definitions together instead of inventing new names in only one file.",
        "- Keep call signatures consistent across files. If the startup entrypoint constructs a service/controller with arguments, that constructor must accept them; otherwise change the launcher call to match the actual constructor.",
        "- Do not emit abstract runtime implementations. Generated runtime files must not contain `raise NotImplementedError`; if you define a contract/base class, also provide and use a concrete implementation in startup, routes, exporters, and tests.",
        "- Build an API signature matrix before returning: every model constructor, service constructor, service method, route handler, exporter function, and test call must use the same required/optional arguments. If a dataclass or class requires values, provide defaults or pass real seed data at every construction site.",
        "- The `--headless --goal --project-name --out` export path must execute the same service method signatures that the service class actually defines.",
        "- If the launcher calls a service method such as `export_project_assets(...)`, that exact method must exist on the service class or the launcher must call the actual implemented method.",
        "- Do not ship TODO, placeholder, stub, pass-only, empty-dict, or not-implemented business modules. Every listed business file must contain real working logic for this user's project goal.",
        "- In `--headless` mode, write real export evidence files into the `--out` directory: at least `workspace_preview.html`, `workspace_snapshot.json`, `interaction_trace.json`, `state_diff.json`, and one script/export file.",
        "- In Python content, do not write f-strings or quoted strings split across physical lines. For multi-line output, append complete one-line strings to a list and use `'\\n'.join(lines)`.",
        "- README must include exact English section headings: `## Project Overview`, `## Implemented`, `## Not Implemented`, `## How To Run`, `## Sample Data`, `## Directory Map`, `## Limitations`. You may add Chinese text under those headings, but do not replace the detectable English headings.",
        "- `sample_data/source_map.json` must include `content_items` with `source` values starting `API:` and `field_sources` with API refs.",
        "- The project must declare its own concrete acceptance criteria, sample-data adequacy criteria, and delivery evidence expectations in generated docs or metadata; do not rely on CTCP to provide project-specific numbers or content rules.",
        "- Sample data must be deep enough to satisfy the generated project's own declared acceptance criteria, with provenance/source metadata when the project claims API-authored content.",
        "- Never repair one failure by emptying sample JSON or dropping README sections; preserve or improve previously passing sample depth, startup docs, import consistency, and export evidence.",
        "- Before returning, mentally validate that every Python file parses with `ast.parse`, every imported symbol resolves, `--help` exits 0, and `--headless` can find sample data relative to the project root.",
        "- Do not use deterministic local templates; author the implementation from the user goal and available context.",
        "- If the runtime asks for a manifest-only or file-content batch phase, follow that narrower phase exactly; the local runtime will merge the provider-authored text files.",
    ]
    if is_gui:
        lines.extend(
            [
                f"- Add a launcher compatibility table before finalizing: every service/controller constructor and public method called by `{entrypoint_name}` must accept exactly those positional/keyword arguments, or accept optional `*args`/`**kwargs` and normalize them safely.",
                f"- `{entrypoint_name}` must not contain unterminated string literals; avoid code like `f\"...` followed by a raw newline before the closing quote.",
                "- Use Python standard library first. For a local desktop GUI prefer `tkinter`; do not import PyQt5, PySide, wxPython, Electron, or other undeclared external GUI packages.",
            ]
        )
    if is_narrative:
        lines.append(
            "- `workspace_preview.html` must visibly include project/sample loader, story/scene/branch editor, character/asset management, and preview/export sections with forms, inputs, buttons/actions, and JavaScript hooks."
        )
    if is_web or is_gui:
        lines.append(
            "- For web/mobile-local projects, include a real `/` HTML page plus `/status` and one command/action endpoint. The `--serve` verifier probe may start a short self-test server, request `/` and `/status` with `urllib`, print the local LAN URL guidance, and exit 0; the README may document how to run a long-lived server mode if implemented."
        )
    lines.extend(
        [
            *previous_failure_lines,
            "Expected file paths from output_contract_freeze:",
            *required_lines,
            "",
        ]
    )
    return lines


def _package_name(*, contract: dict[str, Any], project_root: str) -> str:
    explicit = str(contract.get("package_name", "")).strip()
    if explicit:
        return explicit
    tail = project_root.rstrip("/").rsplit("/", 1)[-1]
    value = "".join(ch if ch.isalnum() else "_" for ch in tail.lower())
    value = "_".join(part for part in value.split("_") if part)
    return value or "project_copilot"


def _previous_failure_lines(run_dir: Path) -> list[str]:
    path = run_dir / "artifacts" / "source_generation_report.json"
    try:
        report = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []
    if not isinstance(report, dict) or str(report.get("status", "")).lower() != "blocked":
        return []
    lines = ["Previous source_generation failed; fix these exact issues:"]
    generic = report.get("generic_validation") if isinstance(report.get("generic_validation"), dict) else {}
    smoke = generic.get("smoke_run") if isinstance(generic.get("smoke_run"), dict) else {}
    for name in ("startup_probe", "export_probe"):
        probe = smoke.get(name) if isinstance(smoke.get(name), dict) else {}
        stderr = str(probe.get("stderr_tail", "") or probe.get("stdout_tail", "")).strip()
        if stderr:
            lines.append(f"- {name}: {stderr[:500]}")
            lines.extend(_runtime_probe_repair_hints(stderr))
    imports = generic.get("python_import_consistency") if isinstance(generic.get("python_import_consistency"), dict) else {}
    missing_symbols = imports.get("missing_symbols") if isinstance(imports.get("missing_symbols"), list) else []
    for row in missing_symbols[:12]:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol", "")).strip()
        target = str(row.get("target_path", "") or row.get("target_module", "")).strip()
        source = str(row.get("from_path", "")).strip()
        if symbol and target:
            lines.append(f"- import_consistency: `{symbol}` imported by `{source}` must be defined or re-exported by `{target}`")
    mismatches = imports.get("interface_contract_mismatches") if isinstance(imports.get("interface_contract_mismatches"), list) else []
    for row in mismatches[:8]:
        if not isinstance(row, dict):
            continue
        path = str(row.get("path", "")).strip()
        reason = str(row.get("reason", "")).strip()
        missing = ", ".join(str(item) for item in row.get("missing_declared_symbols", [])[:8]) if isinstance(row.get("missing_declared_symbols"), list) else ""
        undeclared = ", ".join(str(item) for item in row.get("undeclared_actual_symbols", [])[:8]) if isinstance(row.get("undeclared_actual_symbols"), list) else ""
        details = "; ".join(part for part in (f"missing declared: {missing}" if missing else "", f"undeclared actual: {undeclared}" if undeclared else "") if part)
        if path and reason:
            lines.append(f"- interface_contract: `{path}` {reason}" + (f" ({details})" if details else ""))
    cycles = imports.get("import_cycles") if isinstance(imports.get("import_cycles"), list) else []
    for cycle in cycles[:6]:
        if isinstance(cycle, list) and cycle:
            lines.append("- import_cycle: break this generated Python circular import: " + " -> ".join(str(item) for item in cycle))
    signatures = generic.get("python_signature_consistency") if isinstance(generic.get("python_signature_consistency"), dict) else {}
    signature_mismatches = signatures.get("mismatches") if isinstance(signatures.get("mismatches"), list) else []
    for row in signature_mismatches[:10]:
        if not isinstance(row, dict):
            continue
        caller = str(row.get("caller_path", "")).strip()
        callee = str(row.get("callee", "")).strip()
        signature = str(row.get("signature", "")).strip()
        line = int(row.get("line", 0) or 0)
        missing = ", ".join(str(item) for item in row.get("missing_required", [])[:8]) if isinstance(row.get("missing_required"), list) else ""
        unexpected = ", ".join(str(item) for item in row.get("unexpected_keywords", [])[:8]) if isinstance(row.get("unexpected_keywords"), list) else ""
        parts = [f"missing required: {missing}" if missing else "", f"unexpected keywords: {unexpected}" if unexpected else ""]
        if row.get("too_many_positionals"):
            parts.append("too many positional arguments")
        details = "; ".join(part for part in parts if part)
        if caller and callee:
            lines.append(
                f"- signature_consistency: `{caller}:{line}` calls `{callee}` but target signature is `{signature}`"
                + (f" ({details})" if details else "")
            )
    contract_sig_mismatches = signatures.get("interface_signature_mismatches") if isinstance(signatures.get("interface_signature_mismatches"), list) else []
    for row in contract_sig_mismatches[:10]:
        if isinstance(row, dict):
            lines.append(
                f"- signature_matrix: `{row.get('path', '')}` declares `{row.get('symbol', '')}` as `{row.get('declared_signature', '')}` but actual code is `{row.get('actual_signature', '')}`"
            )
    abstract_stubs = signatures.get("abstract_stub_violations") if isinstance(signatures.get("abstract_stub_violations"), list) else []
    for row in abstract_stubs[:10]:
        if isinstance(row, dict):
            lines.append(
                f"- abstract_stub: `{row.get('path', '')}:{row.get('line', 0)}` `{row.get('symbol', '')}` raises NotImplementedError; replace it with concrete runtime logic or stop routing startup/tests through it"
            )
    generated_tests = generic.get("generated_tests") if isinstance(generic.get("generated_tests"), dict) else {}
    test_violations = generated_tests.get("import_style_violations") if isinstance(generated_tests.get("import_style_violations"), list) else []
    for row in test_violations[:8]:
        if not isinstance(row, dict):
            continue
        path = str(row.get("path", "")).strip()
        imported = str(row.get("import", "")).strip()
        reason = str(row.get("reason", "")).strip()
        if path and imported:
            lines.append(f"- generated_tests: `{path}` uses `{imported}`; {reason or 'import the generated package directly, not src.<package>'}")
    if generated_tests and not bool(generated_tests.get("passed", False)):
        test_text = "\n".join(
            str(generated_tests.get(key, "")).strip()
            for key in ("stdout_tail", "stderr_tail", "reason")
            if str(generated_tests.get(key, "")).strip()
        )
        if test_text:
            lines.append(f"- generated_tests: unittest/self-check failed: {test_text[:700]}")
            lines.extend(_runtime_probe_repair_hints(test_text))
    domain = report.get("domain_validation") if isinstance(report.get("domain_validation"), dict) else {}
    missing = [str(item).strip() for item in domain.get("missing", []) if str(item).strip()] if isinstance(domain.get("missing", []), list) else []
    for item in missing[:8]:
        lines.append(f"- domain: {item}")
    readme = report.get("readme_quality") if isinstance(report.get("readme_quality"), dict) else {}
    readme_missing = [str(item).strip() for item in readme.get("missing_sections", []) if str(item).strip()] if isinstance(readme.get("missing_sections", []), list) else []
    if readme_missing:
        lines.append("- readme_quality: README must include these missing sections exactly enough to be detected: " + ", ".join(readme_missing[:12]))
    readme_reasons = [str(item).strip() for item in readme.get("reasons", []) if str(item).strip()] if isinstance(readme.get("reasons", []), list) else []
    for item in readme_reasons[:4]:
        lines.append(f"- readme_quality: {item}")
    ux = report.get("ux_validation") if isinstance(report.get("ux_validation"), dict) else {}
    reasons = [str(item).strip() for item in ux.get("reasons", []) if str(item).strip()] if isinstance(ux.get("reasons", []), list) else []
    for item in reasons[:6]:
        lines.append(f"- ux: {item}")
        if "gui/web" in item.lower() or "visual evidence" in item.lower() or "preview source page" in item.lower():
            lines.append(
                "- delivery_qa: web/mobile projects must expose a real `/` preview page, `/status`, and export/visual evidence that the verifier can observe"
            )
    return lines if len(lines) > 1 else []


def _runtime_probe_repair_hints(stderr: str) -> list[str]:
    lowered = str(stderr or "").lower()
    hints: list[str] = []
    if "modulenotfounderror" in lowered or "no module named" in lowered:
        hints.append(
            "- dependency: validation probes do not install dependencies; remove the missing external import or replace it with standard-library/local generated code"
        )
        if "no module named 'src." in lowered or 'no module named "src.' in lowered:
            hints.append(
                "- generated_tests: tests are importing `src.<package>`; generated tests must import the package directly with the generated `src` directory on PYTHONPATH"
            )
        if any(marker in lowered for marker in ("no module named 'service'", 'no module named "service"', "no module named 'models'", 'no module named "models"', "no module named 'exporter'", 'no module named "exporter"')):
            hints.append(
                "- integration_qa: this looks like a bare sibling import inside a src-layout package; replace `import service`/`import models` style imports with explicit relative or package imports and update tests/entrypoint PYTHONPATH consistently"
            )
    if "cannot import name" in lowered:
        hints.append(
            "- integration_qa: imported/re-exported symbol is missing; make package `__init__.py`, entrypoint imports, and provider `interfaces` match the actual definitions"
        )
    if "typeerror:" in lowered and "missing" in lowered and "required positional argument" in lowered:
        hints.append(
            "- integration_qa: constructor or method signature mismatch; align every service/model/exporter/test call with the actual required arguments, or add safe defaults and seed-data construction"
        )
    if "typeerror:" in lowered and "unexpected keyword argument" in lowered:
        hints.append(
            "- integration_qa: keyword signature mismatch; rename constructor/function keyword arguments consistently across models, services, entrypoints, exporters, and generated tests"
        )
    if "typeerror:" in lowered and "positional argument" in lowered and "were given" in lowered:
        hints.append(
            "- integration_qa: positional signature mismatch; align call sites with the actual constructor or method signature instead of changing only one file"
        )
    if "actively refused" in lowered or "timed out" in lowered or "connection refused" in lowered:
        hints.append(
            "- delivery_qa: the local server did not become reachable; make `--serve` perform a deterministic startup self-test for `/` and `/status`, and avoid daemon threads that exit before handling requests"
        )
    return hints


def _expected_paths(*, contract: dict[str, Any], project_root: str) -> list[str]:
    keys = (
        "startup_entrypoint",
        "startup_readme",
        "target_files",
        "source_files",
        "doc_files",
        "workflow_files",
        "business_files",
        "acceptance_files",
    )
    out: list[str] = []
    seen: set[str] = set()
    for key in keys:
        value = contract.get(key)
        rows = value if isinstance(value, list) else [value]
        for item in rows:
            path = str(item or "").strip().replace("\\", "/")
            if not path or path in seen or not path.startswith(project_root + "/"):
                continue
            seen.add(path)
            out.append(path)
    return out
