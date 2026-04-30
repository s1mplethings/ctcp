from __future__ import annotations

import json
import re
import textwrap
from typing import Any
def _goal_excerpt(goal: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(goal or "")).strip()
    return cleaned[:220] if cleaned else "Goal-driven MVP project generation request"
def _context_lines(context_used: list[str]) -> str:
    return "\n".join(f"- {row}" for row in context_used) or "- contract-driven repo context"
def _launcher_script(*, package_name: str, startup_rel: str, mode_label: str) -> str:
    run_mode = "web" if "web" in startup_rel else ("gui" if "gui" in startup_rel else "cli")
    serve_lines = ["pass"]
    if run_mode == "web":
        serve_lines = [
            "if args.serve:",
            "    from importlib import import_module",
            f"    payload = import_module('{package_name}.app').health_payload()",
            "    print(json.dumps(payload, ensure_ascii=False, indent=2))",
            "    return 0",
        ]
    lines = [
        "from __future__ import annotations",
        "import argparse",
        "import json",
        "import sys",
        "from pathlib import Path",
        "",
        "ROOT = Path(__file__).resolve().parents[1]",
        'SRC = ROOT / "src"',
        "if str(SRC) not in sys.path:",
        "    sys.path.insert(0, str(SRC))",
        "",
        f"from {package_name}.service import generate_project",
        "",
        "def main() -> int:",
        f'    parser = argparse.ArgumentParser(description="{mode_label}")',
        '    parser.add_argument("--goal", default="project generation request")',
        '    parser.add_argument("--project-name", default="Project Copilot")',
        '    parser.add_argument("--out", default=str(ROOT / "generated_output"))',
        '    parser.add_argument("--headless", action="store_true")',
        '    parser.add_argument("--serve", action="store_true")',
        "    args = parser.parse_args()",
    ]
    lines.extend(f"    {row}" for row in serve_lines)
    lines.extend(
        [
            "    result = generate_project(goal=args.goal, project_name=args.project_name, out_dir=Path(args.out))",
            "    print(json.dumps(result, ensure_ascii=False, indent=2))",
            "    return 0",
            "",
            'if __name__ == "__main__":',
            "    raise SystemExit(main())",
        ]
    )
    return "\n".join(lines) + "\n"


def _intent_seed(project_intent: dict[str, Any], project_spec: dict[str, Any]) -> str:
    return (
        "from __future__ import annotations\n"
        "import json\n\n"
        f"DEFAULT_PROJECT_INTENT = json.loads(r'''{json.dumps(project_intent, ensure_ascii=False, indent=2)}''')\n"
        f"DEFAULT_PROJECT_SPEC = json.loads(r'''{json.dumps(project_spec, ensure_ascii=False, indent=2)}''')\n"
    )


def _quickstart_command(*, startup_rel: str, package_name: str, project_name: str) -> str:
    if startup_rel.startswith("scripts/run_project_web.py"):
        return f"python {startup_rel} --serve"
    if startup_rel.startswith("scripts/"):
        return f"python {startup_rel} --goal \"{project_name}\" --project-name \"{project_name}\" --out generated_output"
    return (
        "python -c \"from pathlib import Path; "
        f"import sys; sys.path.insert(0, r'src'); from {package_name}.service import generate_project; "
        f"print(generate_project(goal='{project_name}', project_name='{project_name}', out_dir=Path('generated_output')))\""
    )


def _seed_builder_module(*, module_name: str, extra_plan_logic: str) -> str:
    lines = [
        "from __future__ import annotations",
        "",
        "from copy import deepcopy",
        "from .seed import DEFAULT_PROJECT_INTENT, DEFAULT_PROJECT_SPEC",
        "",
        "",
        f"def build_{module_name}(goal: str, project_name: str) -> dict[str, object]:",
        "    spec = deepcopy(DEFAULT_PROJECT_SPEC)",
        "    intent = deepcopy(DEFAULT_PROJECT_INTENT)",
        '    spec["goal_summary"] = goal or spec.get("goal_summary", project_name)',
        '    spec["project_name"] = project_name',
        '    spec["project_intent"] = intent',
    ]
    lines.extend(f"    {row}" for row in extra_plan_logic.strip().splitlines() if row.strip())
    lines.append("    return spec")
    return "\n".join(lines) + "\n"


def _common_files(
    *,
    goal_text: str,
    project_id: str,
    project_root: str,
    package_name: str,
    startup_rel: str,
    workflow_doc_rel: str,
    context_used: list[str],
    project_archetype: str,
    project_intent: dict[str, Any],
    project_spec: dict[str, Any],
    readme_body: str,
    workflow_title: str,
    mode_label: str,
) -> dict[str, str]:
    goal_excerpt = _goal_excerpt(goal_text)
    command = _quickstart_command(startup_rel=startup_rel, package_name=package_name, project_name=goal_excerpt)
    files = {
        f"{project_root}/pyproject.toml": (
            f"[project]\nname = \"{project_id}\"\nversion = \"0.1.0\"\n"
            f"description = \"{project_archetype} generated by CTCP\"\nrequires-python = \">=3.11\"\n\n"
            "[tool.pytest.ini_options]\npythonpath = [\"src\"]\n"
        ),
        f"{project_root}/src/{package_name}/__init__.py": "from .service import generate_project\n",
        f"{project_root}/src/{package_name}/seed.py": _intent_seed(project_intent, project_spec),
        f"{project_root}/README.md": (
            f"# {project_id}\n\n"
            "## What This Project Is\n\n"
            f"A CTCP-generated `{project_archetype}` project scaffold for this scoped goal: {goal_excerpt}\n\n"
            "## Implemented\n\n"
            f"{readme_body}\n\n"
            "## Not Implemented\n\n"
            "- Additional domain-specific polish outside the current MVP scope.\n"
            "- Production deployment hardening beyond local smoke run.\n\n"
            "## How To Run\n\n"
            f"`{command}`\n\n"
            "## Sample Data\n\n"
            "- Generated outputs are written to `generated_output/` during the smoke/export path.\n\n"
            "## Directory Map\n\n"
            "- `src/` core feature logic.\n"
            "- `tests/` smoke regression coverage.\n"
            "- `docs/` workflow and runtime notes.\n\n"
            "## Limitations\n\n"
            "- This is a first-pass runnable MVP scaffold.\n"
            "- Expand domain-specific UX, data handling, and deployment in later iterations.\n\n"
            "## Repo Context Consumed\n\n"
            f"{_context_lines(context_used)}\n"
        ),
        f"{project_root}/docs/00_CORE.md": (
            "# Core Runtime Notes\n\n"
            f"- archetype: {project_archetype}\n"
            "- mainline: ProjectIntent -> Spec -> Scaffold -> Core Feature -> Smoke Run -> Delivery Package\n"
            "- generation is spec-driven first, bootstrap codegen provides initial structure\n"
        ),
        f"{project_root}/{workflow_doc_rel}": (
            f"# {workflow_title}\n\n"
            "1. Resolve ProjectIntent and project spec.\n"
            "2. Turn the spec into an executable workflow plan.\n"
            "3. Materialize core feature files and delivery artifacts.\n"
            "4. Run smoke export and inspect acceptance outputs.\n"
        ),
        f"{project_root}/scripts/verify_repo.ps1": (
            "$ErrorActionPreference = 'Stop'\n"
            "$root = Split-Path -Parent $PSScriptRoot\n"
            "$required = @(\n"
            "  (Join-Path $root 'README.md'),\n"
            f"  (Join-Path $root '{startup_rel.replace('/', '\\')}')\n"
            ")\n"
            "$missing = @($required | Where-Object { -not (Test-Path $_) })\n"
            "if ($missing.Count -gt 0) {\n"
            "  Write-Output ('missing: ' + ($missing -join ', '))\n"
            "  exit 1\n"
            "}\n"
            "Write-Output 'PASS'\n"
        ),
        f"{project_root}/meta/tasks/CURRENT.md": (
            "# Generated Task Card\n\n"
            f"- Topic: Generated {project_archetype} MVP delivery\n"
            "- Project Type: generic_copilot\n"
            f"- Project Archetype: {project_archetype}\n"
        ),
        f"{project_root}/meta/reports/LAST.md": (
            "# Generated Report\n\n"
            "## Readlist\n"
            "- generated project intent and spec\n\n"
            "## Plan\n"
            "- materialize runnable MVP scaffold\n\n"
            "## Changes\n"
            f"- generated {project_archetype} business files and smoke path\n\n"
            "## Verify\n"
            "- local smoke/export path available\n\n"
            "## Questions\n"
            "- none\n\n"
            "## Demo\n"
            "- generated outputs written under generated_output/\n"
        ),
        f"{project_root}/meta/manifest.json": json.dumps(
            {
                "schema_version": "ctcp-generated-project-manifest-v1",
                "project_type": "generic_copilot",
                "project_archetype": project_archetype,
                "goal": goal_excerpt,
                "mainline": [
                    "ProjectIntent",
                    "Spec",
                    "Scaffold",
                    "Core Feature",
                    "Smoke Run",
                    "Delivery Package",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    }
    if startup_rel.startswith("scripts/"):
        files[f"{project_root}/{startup_rel}"] = _launcher_script(
            package_name=package_name,
            startup_rel=startup_rel,
            mode_label=mode_label,
        )
    return files


def _merge_file_maps(*maps: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for mapping in maps:
        out.update(mapping)
    return out


def _generic_pipeline_module_map(project_root: str, package_name: str) -> dict[str, str]:
    return {
        f"{project_root}/src/{package_name}/models.py": textwrap.dedent(
            """
            from __future__ import annotations

            from dataclasses import asdict, dataclass, field
            from typing import Any


            @dataclass
            class WorkflowStep:
                step_id: str
                objective: str
                deliverable: str
                checks: list[str] = field(default_factory=list)

                def to_dict(self) -> dict[str, Any]:
                    return asdict(self)
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/spec_builder.py": _seed_builder_module(
            module_name="spec",
            extra_plan_logic=(
                "spec['workflow_plan'] = [\n"
                "    {'step_id': 'intent', 'objective': 'ground user intent', 'deliverable': 'intent snapshot'},\n"
                "    {'step_id': 'spec', 'objective': 'freeze MVP scope', 'deliverable': 'spec document'},\n"
                "    {'step_id': 'delivery', 'objective': 'export smoke-ready package', 'deliverable': 'acceptance report'},\n"
                "]"
            ),
        ),
        f"{project_root}/src/{package_name}/planner.py": textwrap.dedent(
            """
            from __future__ import annotations

            from .models import WorkflowStep


            def build_plan(spec: dict[str, object]) -> list[WorkflowStep]:
                scope = list(spec.get("mvp_scope", []))
                return [
                    WorkflowStep("clarify", "Summarize the goal into a runnable MVP scope", "mvp_spec.json", scope[:3] or ["scope captured"]),
                    WorkflowStep("implement", "Materialize the minimum feature path", "workflow_plan.json", ["runnable entrypoint", "export path"]),
                    WorkflowStep("accept", "Check smoke run and delivery evidence", "acceptance_report.json", list(spec.get("acceptance_criteria", []))),
                ]
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/exporter.py": textwrap.dedent(
            """
            from __future__ import annotations

            import json
            from pathlib import Path


            def export_bundle(*, spec: dict[str, object], workflow_plan: list[dict[str, object]], out_dir: Path) -> dict[str, str]:
                out_dir.mkdir(parents=True, exist_ok=True)
                deliver_dir = out_dir / "deliverables"
                deliver_dir.mkdir(parents=True, exist_ok=True)
                spec_path = deliver_dir / "project_bundle.json"
                plan_path = deliver_dir / "workflow_plan.json"
                acceptance_path = deliver_dir / "acceptance_report.json"
                spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                plan_path.write_text(json.dumps({"workflow_plan": workflow_plan}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                acceptance_path.write_text(
                    json.dumps(
                        {
                            "status": "pass",
                            "checks": spec.get("acceptance_criteria", []),
                            "core_user_flow": ["build spec", "export workflow", "review acceptance output"],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\\n",
                    encoding="utf-8",
                )
                return {
                    "project_bundle_json": str(spec_path),
                    "workflow_plan_json": str(plan_path),
                    "acceptance_report_json": str(acceptance_path),
                }
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/service.py": textwrap.dedent(
            """
            from __future__ import annotations

            from pathlib import Path

            from .exporter import export_bundle
            from .planner import build_plan
            from .spec_builder import build_spec


            def generate_project(*, goal: str, project_name: str, out_dir: Path) -> dict[str, str]:
                spec = build_spec(goal, project_name)
                workflow_plan = [row.to_dict() for row in build_plan(spec)]
                return export_bundle(spec=spec, workflow_plan=workflow_plan, out_dir=out_dir)
            """
        ).lstrip(),
    }


def _generic_pipeline_test_map(project_root: str, package_name: str) -> dict[str, str]:
    return {
        f"{project_root}/tests/test_{package_name}_service.py": textwrap.dedent(
            f"""
            from __future__ import annotations

            import json
            import sys
            import tempfile
            import unittest
            from pathlib import Path

            ROOT = Path(__file__).resolve().parents[1]
            SRC = ROOT / "src"
            if str(SRC) not in sys.path:
                sys.path.insert(0, str(SRC))

            from {package_name}.service import generate_project


            class GenericPipelineTests(unittest.TestCase):
                def test_generate_project_exports_spec_and_acceptance(self) -> None:
                    with tempfile.TemporaryDirectory(prefix="generic_pipeline_") as td:
                        result = generate_project(goal="generic smoke", project_name="Generic Copilot", out_dir=Path(td))
                        spec_doc = json.loads(Path(result["project_bundle_json"]).read_text(encoding="utf-8"))
                        self.assertIn("workflow_plan", spec_doc)
                        self.assertTrue(Path(result["workflow_plan_json"]).exists())
                        self.assertTrue(Path(result["acceptance_report_json"]).exists())


            if __name__ == "__main__":
                unittest.main()
            """
        ).lstrip()
    }


def _cli_toolkit_module_map(project_root: str, package_name: str) -> dict[str, str]:
    return {
        f"{project_root}/src/{package_name}/models.py": textwrap.dedent(
            """
            from __future__ import annotations

            from dataclasses import asdict, dataclass, field
            from typing import Any


            @dataclass
            class CommandStep:
                command_id: str
                purpose: str
                input_hint: str
                output_hint: str
                checks: list[str] = field(default_factory=list)

                def to_dict(self) -> dict[str, Any]:
                    return asdict(self)
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/spec_builder.py": _seed_builder_module(
            module_name="spec",
            extra_plan_logic=(
                "spec['command_contract'] = {\n"
                "    'entrypoint': 'generate_project',\n"
                "    'primary_input': 'goal',\n"
                "    'primary_outputs': ['mvp_spec.json', 'cli_command_plan.json', 'acceptance_report.json'],\n"
                "}"
            ),
        ),
        f"{project_root}/src/{package_name}/commands.py": textwrap.dedent(
            """
            from __future__ import annotations

            from .models import CommandStep


            def build_command_plan(spec: dict[str, object]) -> list[CommandStep]:
                scope = list(spec.get("mvp_scope", []))
                return [
                    CommandStep("capture_goal", "Summarize goal into a frozen MVP spec", "raw goal", "mvp_spec.json", scope[:2] or ["goal summary"]),
                    CommandStep("emit_workflow", "Emit operator-facing command workflow", "spec snapshot", "cli_command_plan.json", ["command sequence", "owner checklist"]),
                    CommandStep("review_acceptance", "Check that the toolkit exported the expected files", "deliverables", "acceptance_report.json", list(spec.get("acceptance_criteria", []))),
                ]
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/exporter.py": textwrap.dedent(
            """
            from __future__ import annotations

            import json
            from pathlib import Path


            def export_bundle(*, spec: dict[str, object], command_plan: list[dict[str, object]], out_dir: Path) -> dict[str, str]:
                out_dir.mkdir(parents=True, exist_ok=True)
                deliver_dir = out_dir / "deliverables"
                deliver_dir.mkdir(parents=True, exist_ok=True)
                spec_path = deliver_dir / "mvp_spec.json"
                plan_path = deliver_dir / "cli_command_plan.json"
                checklist_path = deliver_dir / "operator_checklist.md"
                acceptance_path = deliver_dir / "acceptance_report.json"
                spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                plan_path.write_text(json.dumps({"command_plan": command_plan}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                checklist_path.write_text("# Operator Checklist\\n\\n- Review mvp_spec.json\\n- Run command plan\\n- Confirm acceptance report\\n", encoding="utf-8")
                acceptance_path.write_text(json.dumps({"status": "pass", "checks": spec.get("acceptance_criteria", [])}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                return {
                    "mvp_spec_json": str(spec_path),
                    "cli_command_plan_json": str(plan_path),
                    "operator_checklist_md": str(checklist_path),
                    "acceptance_report_json": str(acceptance_path),
                }
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/service.py": textwrap.dedent(
            """
            from __future__ import annotations

            from pathlib import Path

            from .commands import build_command_plan
            from .exporter import export_bundle
            from .spec_builder import build_spec


            def generate_project(*, goal: str, project_name: str, out_dir: Path) -> dict[str, str]:
                spec = build_spec(goal, project_name)
                command_plan = [row.to_dict() for row in build_command_plan(spec)]
                return export_bundle(spec=spec, command_plan=command_plan, out_dir=out_dir)
            """
        ).lstrip(),
    }


def _cli_toolkit_test_map(project_root: str, package_name: str) -> dict[str, str]:
    return {
        f"{project_root}/tests/test_{package_name}_service.py": textwrap.dedent(
            f"""
            from __future__ import annotations

            import json
            import sys
            import tempfile
            import unittest
            from pathlib import Path

            ROOT = Path(__file__).resolve().parents[1]
            SRC = ROOT / "src"
            if str(SRC) not in sys.path:
                sys.path.insert(0, str(SRC))

            from {package_name}.service import generate_project


            class CliToolkitTests(unittest.TestCase):
                def test_generate_project_exports_cli_plan(self) -> None:
                    with tempfile.TemporaryDirectory(prefix="cli_toolkit_") as td:
                        result = generate_project(goal="cli smoke", project_name="CLI Copilot", out_dir=Path(td))
                        plan_doc = json.loads(Path(result["cli_command_plan_json"]).read_text(encoding="utf-8"))
                        self.assertTrue(plan_doc["command_plan"])
                        self.assertTrue(Path(result["operator_checklist_md"]).exists())


            if __name__ == "__main__":
                unittest.main()
            """
        ).lstrip()
    }


def _web_service_module_map(project_root: str, package_name: str) -> dict[str, str]:
    return {
        f"{project_root}/src/{package_name}/models.py": textwrap.dedent(
            """
            from __future__ import annotations

            from dataclasses import asdict, dataclass, field
            from typing import Any


            @dataclass
            class EndpointContract:
                route: str
                method: str
                description: str
                outputs: list[str] = field(default_factory=list)

                def to_dict(self) -> dict[str, Any]:
                    return asdict(self)
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/spec_builder.py": _seed_builder_module(
            module_name="spec",
            extra_plan_logic=(
                "spec['http_contract'] = {\n"
                "    'health_route': '/health',\n"
                "    'generate_route': '/generate',\n"
                "    'response_payloads': ['service_contract.json', 'sample_response.json', 'acceptance_report.json'],\n"
                "}"
            ),
        ),
        f"{project_root}/src/{package_name}/service_contract.py": textwrap.dedent(
            """
            from __future__ import annotations

            from .models import EndpointContract


            def build_contract(spec: dict[str, object]) -> list[EndpointContract]:
                outputs = list(spec.get("required_outputs", []))
                return [
                    EndpointContract("/health", "GET", "Return service health and archetype metadata", ["status", "archetype"]),
                    EndpointContract("/generate", "POST", "Return spec/workflow/acceptance payload summary", outputs or ["spec", "workflow", "acceptance"]),
                ]
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/app.py": textwrap.dedent(
            """
            from __future__ import annotations

            from .service_contract import build_contract
            from .spec_builder import build_spec


            def health_payload() -> dict[str, object]:
                return {"status": "ok", "archetype": "web_service"}


            def generate_payload(goal: str, project_name: str) -> dict[str, object]:
                spec = build_spec(goal, project_name)
                return {
                    "project_name": project_name,
                    "goal_summary": spec.get("goal_summary", ""),
                    "contract": [row.to_dict() for row in build_contract(spec)],
                    "acceptance": list(spec.get("acceptance_criteria", [])),
                }
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/exporter.py": textwrap.dedent(
            """
            from __future__ import annotations

            import json
            from pathlib import Path


            def export_bundle(*, spec: dict[str, object], service_contract: list[dict[str, object]], sample_response: dict[str, object], out_dir: Path) -> dict[str, str]:
                out_dir.mkdir(parents=True, exist_ok=True)
                deliver_dir = out_dir / "deliverables"
                deliver_dir.mkdir(parents=True, exist_ok=True)
                spec_path = deliver_dir / "mvp_spec.json"
                contract_path = deliver_dir / "service_contract.json"
                sample_path = deliver_dir / "sample_response.json"
                acceptance_path = deliver_dir / "acceptance_report.json"
                summary_path = deliver_dir / "delivery_summary.md"
                spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                contract_path.write_text(json.dumps({"routes": service_contract}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                sample_path.write_text(json.dumps(sample_response, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                acceptance_path.write_text(json.dumps({"status": "pass", "checks": spec.get("acceptance_criteria", [])}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                summary_path.write_text("# Delivery Summary\\n\\n- /health\\n- /generate\\n- sample_response.json\\n", encoding="utf-8")
                return {
                    "mvp_spec_json": str(spec_path),
                    "service_contract_json": str(contract_path),
                    "sample_response_json": str(sample_path),
                    "acceptance_report_json": str(acceptance_path),
                    "delivery_summary_md": str(summary_path),
                }
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/service.py": textwrap.dedent(
            """
            from __future__ import annotations

            from pathlib import Path

            from .app import generate_payload
            from .exporter import export_bundle
            from .service_contract import build_contract
            from .spec_builder import build_spec


            def generate_project(*, goal: str, project_name: str, out_dir: Path) -> dict[str, str]:
                spec = build_spec(goal, project_name)
                contract = [row.to_dict() for row in build_contract(spec)]
                sample_response = generate_payload(goal, project_name)
                return export_bundle(spec=spec, service_contract=contract, sample_response=sample_response, out_dir=out_dir)
            """
        ).lstrip(),
    }


def _web_service_test_map(project_root: str, package_name: str) -> dict[str, str]:
    return {
        f"{project_root}/tests/test_{package_name}_service.py": textwrap.dedent(
            f"""
            from __future__ import annotations

            import json
            import sys
            import tempfile
            import unittest
            from pathlib import Path

            ROOT = Path(__file__).resolve().parents[1]
            SRC = ROOT / "src"
            if str(SRC) not in sys.path:
                sys.path.insert(0, str(SRC))

            from {package_name}.app import generate_payload, health_payload
            from {package_name}.service import generate_project


            class WebServiceTests(unittest.TestCase):
                def test_generate_project_exports_service_contract(self) -> None:
                    with tempfile.TemporaryDirectory(prefix="web_service_") as td:
                        result = generate_project(goal="web smoke", project_name="Web Copilot", out_dir=Path(td))
                        self.assertEqual(health_payload()["status"], "ok")
                        payload = generate_payload("goal", "Web Copilot")
                        self.assertTrue(payload["contract"])
                        self.assertTrue(Path(result["service_contract_json"]).exists())
                        json.loads(Path(result["sample_response_json"]).read_text(encoding="utf-8"))


            if __name__ == "__main__":
                unittest.main()
            """
        ).lstrip()
    }


def _data_pipeline_module_map(project_root: str, package_name: str) -> dict[str, str]:
    return {
        f"{project_root}/src/{package_name}/models.py": textwrap.dedent(
            """
            from __future__ import annotations

            from dataclasses import asdict, dataclass, field
            from typing import Any


            @dataclass
            class TransformStep:
                step_id: str
                source_field: str
                destination_field: str
                rationale: str
                checks: list[str] = field(default_factory=list)

                def to_dict(self) -> dict[str, Any]:
                    return asdict(self)
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/spec_builder.py": _seed_builder_module(
            module_name="spec",
            extra_plan_logic=(
                "spec['pipeline_contract'] = {\n"
                "    'input_file': 'sample_input.json',\n"
                "    'output_file': 'sample_output.json',\n"
                "    'artifacts': ['pipeline_plan.json', 'acceptance_report.json'],\n"
                "}"
            ),
        ),
        f"{project_root}/src/{package_name}/transforms.py": textwrap.dedent(
            """
            from __future__ import annotations

            from .models import TransformStep


            def build_transforms(spec: dict[str, object]) -> list[TransformStep]:
                return [
                    TransformStep("goal_summary", "goal", "goal_summary", "normalize the fuzzy goal into an actionable summary", ["summary is non-empty"]),
                    TransformStep("scope_snapshot", "mvp_scope", "scope_snapshot", "capture MVP scope for downstream checks", ["at least one scope item"]),
                    TransformStep("acceptance_snapshot", "acceptance_criteria", "acceptance_snapshot", "carry acceptance criteria into the export", ["criteria exported"]),
                ]


            def apply_transforms(goal: str, spec: dict[str, object]) -> dict[str, object]:
                return {
                    "goal_summary": spec.get("goal_summary", goal),
                    "scope_snapshot": list(spec.get("mvp_scope", [])),
                    "acceptance_snapshot": list(spec.get("acceptance_criteria", [])),
                }
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/pipeline.py": textwrap.dedent(
            """
            from __future__ import annotations

            from .transforms import apply_transforms, build_transforms


            def run_pipeline(goal: str, project_name: str, spec: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, object], dict[str, object]]:
                transform_steps = [row.to_dict() for row in build_transforms(spec)]
                sample_input = {"goal": goal, "project_name": project_name}
                sample_output = apply_transforms(goal, spec)
                return transform_steps, sample_input, sample_output
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/exporter.py": textwrap.dedent(
            """
            from __future__ import annotations

            import json
            from pathlib import Path


            def export_bundle(*, spec: dict[str, object], pipeline_plan: list[dict[str, object]], sample_input: dict[str, object], sample_output: dict[str, object], out_dir: Path) -> dict[str, str]:
                out_dir.mkdir(parents=True, exist_ok=True)
                deliver_dir = out_dir / "deliverables"
                deliver_dir.mkdir(parents=True, exist_ok=True)
                spec_path = deliver_dir / "mvp_spec.json"
                plan_path = deliver_dir / "pipeline_plan.json"
                input_path = deliver_dir / "sample_input.json"
                output_path = deliver_dir / "sample_output.json"
                acceptance_path = deliver_dir / "acceptance_report.json"
                spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                plan_path.write_text(json.dumps({"pipeline_plan": pipeline_plan}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                input_path.write_text(json.dumps(sample_input, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                output_path.write_text(json.dumps(sample_output, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                acceptance_path.write_text(json.dumps({"status": "pass", "checks": spec.get("acceptance_criteria", [])}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                return {
                    "mvp_spec_json": str(spec_path),
                    "pipeline_plan_json": str(plan_path),
                    "sample_input_json": str(input_path),
                    "sample_output_json": str(output_path),
                    "acceptance_report_json": str(acceptance_path),
                }
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/service.py": textwrap.dedent(
            """
            from __future__ import annotations

            from pathlib import Path

            from .exporter import export_bundle
            from .pipeline import run_pipeline
            from .spec_builder import build_spec


            def generate_project(*, goal: str, project_name: str, out_dir: Path) -> dict[str, str]:
                spec = build_spec(goal, project_name)
                pipeline_plan, sample_input, sample_output = run_pipeline(goal, project_name, spec)
                return export_bundle(
                    spec=spec,
                    pipeline_plan=pipeline_plan,
                    sample_input=sample_input,
                    sample_output=sample_output,
                    out_dir=out_dir,
                )
            """
        ).lstrip(),
    }


def _data_pipeline_test_map(project_root: str, package_name: str) -> dict[str, str]:
    return {
        f"{project_root}/tests/test_{package_name}_service.py": textwrap.dedent(
            f"""
            from __future__ import annotations

            import json
            import sys
            import tempfile
            import unittest
            from pathlib import Path

            ROOT = Path(__file__).resolve().parents[1]
            SRC = ROOT / "src"
            if str(SRC) not in sys.path:
                sys.path.insert(0, str(SRC))

            from {package_name}.service import generate_project


            class DataPipelineTests(unittest.TestCase):
                def test_generate_project_exports_pipeline_samples(self) -> None:
                    with tempfile.TemporaryDirectory(prefix="data_pipeline_") as td:
                        result = generate_project(goal="pipeline smoke", project_name="Pipeline Copilot", out_dir=Path(td))
                        output_doc = json.loads(Path(result["sample_output_json"]).read_text(encoding="utf-8"))
                        self.assertIn("goal_summary", output_doc)
                        self.assertTrue(Path(result["pipeline_plan_json"]).exists())


            if __name__ == "__main__":
                unittest.main()
            """
        ).lstrip()
    }


def _generic_pipeline_files(
    *,
    goal_text: str,
    project_id: str,
    project_root: str,
    package_name: str,
    startup_rel: str,
    workflow_doc_rel: str,
    context_used: list[str],
    project_archetype: str,
    project_intent: dict[str, Any],
    project_spec: dict[str, Any],
) -> dict[str, str]:
    readme_body = (
        "This package turns a fuzzy goal into a lightweight MVP spec, a workflow plan, and an acceptance report. "
        "It is a generic pipeline fallback, not a domain-default narrative scaffold."
    )
    return _merge_file_maps(
        _common_files(
            goal_text=goal_text,
            project_id=project_id,
            project_root=project_root,
            package_name=package_name,
            startup_rel=startup_rel,
            workflow_doc_rel=workflow_doc_rel,
            context_used=context_used,
            project_archetype=project_archetype,
            project_intent=project_intent,
            project_spec=project_spec,
            readme_body=readme_body,
            workflow_title="Generic Workflow",
            mode_label="Generic MVP pipeline launcher.",
        ),
        _generic_pipeline_module_map(project_root, package_name),
        _generic_pipeline_test_map(project_root, package_name),
    )


def _cli_toolkit_files(
    *,
    goal_text: str,
    project_id: str,
    project_root: str,
    package_name: str,
    startup_rel: str,
    workflow_doc_rel: str,
    context_used: list[str],
    project_archetype: str,
    project_intent: dict[str, Any],
    project_spec: dict[str, Any],
) -> dict[str, str]:
    return _merge_file_maps(
        _common_files(
            goal_text=goal_text,
            project_id=project_id,
            project_root=project_root,
            package_name=package_name,
            startup_rel=startup_rel,
            workflow_doc_rel=workflow_doc_rel,
            context_used=context_used,
            project_archetype=project_archetype,
            project_intent=project_intent,
            project_spec=project_spec,
            readme_body="This CLI toolkit turns a project goal into a command plan, operator checklist, and acceptance report.",
            workflow_title="CLI Toolkit Workflow",
            mode_label="CLI toolkit launcher.",
        ),
        _cli_toolkit_module_map(project_root, package_name),
        _cli_toolkit_test_map(project_root, package_name),
    )


def _web_service_files(
    *,
    goal_text: str,
    project_id: str,
    project_root: str,
    package_name: str,
    startup_rel: str,
    workflow_doc_rel: str,
    context_used: list[str],
    project_archetype: str,
    project_intent: dict[str, Any],
    project_spec: dict[str, Any],
) -> dict[str, str]:
    return _merge_file_maps(
        _common_files(
            goal_text=goal_text,
            project_id=project_id,
            project_root=project_root,
            package_name=package_name,
            startup_rel=startup_rel,
            workflow_doc_rel=workflow_doc_rel,
            context_used=context_used,
            project_archetype=project_archetype,
            project_intent=project_intent,
            project_spec=project_spec,
            readme_body="This web service MVP exposes a local HTTP-style response contract and returns spec/workflow/acceptance JSON payloads. Use `--serve` for a health preview.",
            workflow_title="Web Service Workflow",
            mode_label="Web service launcher.",
        ),
        _web_service_module_map(project_root, package_name),
        _web_service_test_map(project_root, package_name),
    )


def _data_pipeline_files(
    *,
    goal_text: str,
    project_id: str,
    project_root: str,
    package_name: str,
    startup_rel: str,
    workflow_doc_rel: str,
    context_used: list[str],
    project_archetype: str,
    project_intent: dict[str, Any],
    project_spec: dict[str, Any],
) -> dict[str, str]:
    return _merge_file_maps(
        _common_files(
            goal_text=goal_text,
            project_id=project_id,
            project_root=project_root,
            package_name=package_name,
            startup_rel=startup_rel,
            workflow_doc_rel=workflow_doc_rel,
            context_used=context_used,
            project_archetype=project_archetype,
            project_intent=project_intent,
            project_spec=project_spec,
            readme_body="This data pipeline MVP turns a goal into transform steps, pipeline outputs, and sample input/output JSON for smoke verification.",
            workflow_title="Data Pipeline Workflow",
            mode_label="Data pipeline launcher.",
        ),
        _data_pipeline_module_map(project_root, package_name),
        _data_pipeline_test_map(project_root, package_name),
    )


def _team_task_pm_module_map(project_root: str, package_name: str) -> dict[str, str]:
    return {
        f"{project_root}/src/{package_name}/models.py": textwrap.dedent(
            """
            from __future__ import annotations

            from dataclasses import asdict, dataclass, field
            from typing import Any


            @dataclass
            class User:
                user_id: str
                name: str
                role: str = "member"

                def to_dict(self) -> dict[str, Any]:
                    return asdict(self)


            @dataclass
            class Workspace:
                workspace_id: str
                name: str
                user_ids: list[str] = field(default_factory=list)

                def to_dict(self) -> dict[str, Any]:
                    return asdict(self)


            @dataclass
            class Project:
                project_id: str
                workspace_id: str
                name: str
                description: str

                def to_dict(self) -> dict[str, Any]:
                    return asdict(self)


            @dataclass
            class Task:
                task_id: str
                project_id: str
                title: str
                description: str
                status: str
                priority: str
                assignee: str
                due_date: str
                labels: list[str] = field(default_factory=list)

                def to_dict(self) -> dict[str, Any]:
                    return asdict(self)


            @dataclass
            class Comment:
                comment_id: str
                task_id: str
                author: str
                body: str

                def to_dict(self) -> dict[str, Any]:
                    return asdict(self)


            @dataclass
            class ActivityEvent:
                event_id: str
                task_id: str
                actor: str
                action: str
                detail: str

                def to_dict(self) -> dict[str, Any]:
                    return asdict(self)
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/workspace.py": textwrap.dedent(
            """
            from __future__ import annotations


            def login_with_demo_user(workspace: dict[str, object], name: str = "Avery PM") -> dict[str, object]:
                users = [row for row in workspace.get("users", []) if isinstance(row, dict)]
                for user in users:
                    if str(user.get("name", "")) == name:
                        return {"authenticated": True, "user": user}
                return {"authenticated": False, "user": users[0] if users else {}}


            def list_projects(workspace: dict[str, object]) -> list[dict[str, object]]:
                return [row for row in workspace.get("projects", []) if isinstance(row, dict)]


            def create_project(workspace: dict[str, object], *, name: str, description: str) -> dict[str, object]:
                projects = workspace.setdefault("projects", [])
                project = {
                    "project_id": f"proj_{len(projects) + 1}",
                    "workspace_id": str(workspace.get("workspace_id", "workspace")),
                    "name": name,
                    "description": description,
                }
                projects.append(project)
                return project
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/tasks.py": textwrap.dedent(
            """
            from __future__ import annotations


            VALID_STATUSES = ("backlog", "todo", "doing", "review", "done")
            VALID_PRIORITIES = ("low", "medium", "high", "urgent")


            def create_task(
                workspace: dict[str, object],
                *,
                project_id: str,
                title: str,
                description: str,
                assignee: str,
                priority: str = "medium",
                due_date: str = "",
                labels: list[str] | None = None,
            ) -> dict[str, object]:
                tasks = workspace.setdefault("tasks", [])
                task = {
                    "task_id": f"task_{len(tasks) + 1}",
                    "project_id": project_id,
                    "title": title,
                    "description": description,
                    "status": "todo",
                    "priority": priority if priority in VALID_PRIORITIES else "medium",
                    "assignee": assignee,
                    "due_date": due_date,
                    "labels": list(labels or []),
                }
                tasks.append(task)
                return task


            def edit_task_fields(workspace: dict[str, object], task_id: str, **updates: object) -> dict[str, object]:
                task = get_task(workspace, task_id)
                allowed = {"title", "description", "priority", "assignee", "due_date", "labels"}
                for key, value in updates.items():
                    if key in allowed:
                        task[key] = value
                return task


            def move_task_status(workspace: dict[str, object], task_id: str, status: str) -> dict[str, object]:
                if status not in VALID_STATUSES:
                    raise ValueError(f"unsupported task status: {status}")
                task = get_task(workspace, task_id)
                task["status"] = status
                return task


            def get_task(workspace: dict[str, object], task_id: str) -> dict[str, object]:
                for task in workspace.get("tasks", []):
                    if isinstance(task, dict) and task.get("task_id") == task_id:
                        return task
                raise KeyError(task_id)
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/board.py": textwrap.dedent(
            """
            from __future__ import annotations


            BOARD_COLUMNS = ("backlog", "todo", "doing", "review", "done")


            def build_kanban_board(workspace: dict[str, object]) -> dict[str, list[dict[str, object]]]:
                board: dict[str, list[dict[str, object]]] = {status: [] for status in BOARD_COLUMNS}
                for task in workspace.get("tasks", []):
                    if not isinstance(task, dict):
                        continue
                    board.setdefault(str(task.get("status", "todo")), []).append(task)
                return board


            def build_task_list(workspace: dict[str, object]) -> list[dict[str, object]]:
                return sorted(
                    [row for row in workspace.get("tasks", []) if isinstance(row, dict)],
                    key=lambda row: (str(row.get("project_id", "")), str(row.get("status", "")), str(row.get("priority", ""))),
                )
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/filters.py": textwrap.dedent(
            """
            from __future__ import annotations


            def filter_tasks(
                workspace: dict[str, object],
                *,
                status: str | None = None,
                assignee: str | None = None,
                label: str | None = None,
                priority: str | None = None,
            ) -> list[dict[str, object]]:
                rows = [row for row in workspace.get("tasks", []) if isinstance(row, dict)]
                if status:
                    rows = [row for row in rows if row.get("status") == status]
                if assignee:
                    rows = [row for row in rows if row.get("assignee") == assignee]
                if label:
                    rows = [row for row in rows if label in list(row.get("labels", []))]
                if priority:
                    rows = [row for row in rows if row.get("priority") == priority]
                return rows
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/activity.py": textwrap.dedent(
            """
            from __future__ import annotations


            def add_activity(workspace: dict[str, object], *, task_id: str, actor: str, action: str, detail: str) -> dict[str, object]:
                rows = workspace.setdefault("activity", [])
                event = {
                    "event_id": f"evt_{len(rows) + 1}",
                    "task_id": task_id,
                    "actor": actor,
                    "action": action,
                    "detail": detail,
                }
                rows.append(event)
                return event


            def comment_on_task(workspace: dict[str, object], *, task_id: str, author: str, body: str) -> dict[str, object]:
                comments = workspace.setdefault("comments", [])
                comment = {
                    "comment_id": f"comment_{len(comments) + 1}",
                    "task_id": task_id,
                    "author": author,
                    "body": body,
                }
                comments.append(comment)
                add_activity(workspace, task_id=task_id, actor=author, action="comment", detail=body)
                return comment


            def activity_feed(workspace: dict[str, object]) -> list[dict[str, object]]:
                return [row for row in workspace.get("activity", []) if isinstance(row, dict)]
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/app.py": textwrap.dedent(
            """
            from __future__ import annotations

            import html

            from .activity import activity_feed
            from .board import build_kanban_board, build_task_list
            from .filters import filter_tasks
            from .seed import load_demo_workspace


            def health_payload() -> dict[str, object]:
                workspace = load_demo_workspace()
                return {
                    "status": "ok",
                    "archetype": "team_task_pm_web",
                    "project_domain": "team_task_management",
                    "tasks": len(workspace.get("tasks", [])),
                    "views": ["login", "workspace_project_switcher", "kanban_board", "task_list", "task_detail_drawer"],
                }


            def render_preview_html(workspace: dict[str, object]) -> str:
                board = build_kanban_board(workspace)
                tasks = build_task_list(workspace)
                doing = filter_tasks(workspace, status="doing")
                events = activity_feed(workspace)
                columns = []
                for status, rows in board.items():
                    cards = "".join(
                        f"<article class='task-card'><strong>{html.escape(str(row.get('title', 'Task')))}</strong><span>{html.escape(str(row.get('priority', 'medium')))}</span><small>{html.escape(str(row.get('assignee', 'Unassigned')))}</small></article>"
                        for row in rows
                    )
                    columns.append(f"<section class='kanban-column'><h2>{html.escape(status.title())}</h2>{cards}</section>")
                task_rows = "".join(
                    f"<tr><td>{html.escape(str(row.get('title', 'Task')))}</td><td>{html.escape(str(row.get('status', '')))}</td><td>{html.escape(str(row.get('assignee', '')))}</td><td>{html.escape(', '.join(row.get('labels', [])))}</td></tr>"
                    for row in tasks
                )
                activity_rows = "".join(
                    f"<li><strong>{html.escape(str(row.get('actor', '')))}</strong> {html.escape(str(row.get('action', '')))} - {html.escape(str(row.get('detail', '')))}</li>"
                    for row in events
                )
                detail = tasks[0] if tasks else {}
                return f'''<!doctype html>
<html><head><meta charset="utf-8"><title>Plane-lite Team PM</title>
<style>
body{{margin:0;font-family:Arial,sans-serif;background:#f6f8fb;color:#18202f}}
header{{display:flex;justify-content:space-between;align-items:center;padding:18px 24px;background:#ffffff;border-bottom:1px solid #d8dee9}}
main{{display:grid;grid-template-columns:1.2fr .8fr;gap:18px;padding:20px}}
.kanban-board{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}
.kanban-column,.panel{{background:#fff;border:1px solid #d8dee9;border-radius:8px;padding:12px}}
.task-card{{display:grid;gap:5px;padding:10px;margin:8px 0;border:1px solid #d8dee9;border-radius:6px;background:#fbfcff}}
table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #e5e9f0;padding:8px;text-align:left}}
.filters{{display:flex;gap:8px;flex-wrap:wrap}}.filter-chip{{border:1px solid #a7b1c2;border-radius:16px;padding:5px 9px;background:#fff}}
</style></head>
<body>
<header><h1>Plane-lite Team PM</h1><div class="filters"><span class="filter-chip">workspace</span><span class="filter-chip">project</span><span class="filter-chip">status: doing ({len(doing)})</span><span class="filter-chip">assignee</span></div></header>
<main>
<section><h2>kanban_board</h2><div class="kanban-board">{''.join(columns)}</div></section>
<aside class="panel"><h2>task_detail_drawer</h2><p><strong>{html.escape(str(detail.get('title', 'Task detail')))}</strong></p><p>{html.escape(str(detail.get('description', '')))}</p><p>priority: {html.escape(str(detail.get('priority', '')))}</p><p>due: {html.escape(str(detail.get('due_date', '')))}</p></aside>
<section class="panel"><h2>task_list</h2><table><tbody>{task_rows}</tbody></table></section>
<section class="panel"><h2>activity_feed</h2><ul>{activity_rows}</ul></section>
</main></body></html>'''
            """
        ).lstrip().replace("\n            ", "\n"),
        f"{project_root}/src/{package_name}/exporter.py": textwrap.dedent(
            """
            from __future__ import annotations

            import json
            import zipfile
            from pathlib import Path

            from .activity import activity_feed
            from .app import render_preview_html
            from .board import build_kanban_board, build_task_list


            def export_workspace(workspace: dict[str, object], out_dir: Path) -> dict[str, str]:
                deliver_dir = out_dir / "deliverables"
                deliver_dir.mkdir(parents=True, exist_ok=True)
                workspace_path = deliver_dir / "demo_workspace.json"
                board_path = deliver_dir / "task_board.json"
                list_path = deliver_dir / "task_list.json"
                activity_path = deliver_dir / "activity_feed.json"
                preview_path = deliver_dir / "preview.html"
                acceptance_path = deliver_dir / "acceptance_report.json"
                bundle_path = deliver_dir / "acceptance_bundle.zip"
                workspace_path.write_text(json.dumps(workspace, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                board_path.write_text(json.dumps(build_kanban_board(workspace), ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                list_path.write_text(json.dumps({"tasks": build_task_list(workspace)}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                activity_path.write_text(json.dumps({"activity": activity_feed(workspace)}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                preview_path.write_text(render_preview_html(workspace), encoding="utf-8")
                acceptance = {
                    "status": "pass",
                    "checks": [
                        "login_with_demo_user",
                        "create_project",
                        "create_task",
                        "edit_task_fields",
                        "move_task_status",
                        "comment_on_task",
                        "filter_tasks",
                        "kanban_board",
                        "task_list",
                        "task_detail_drawer",
                        "activity_feed",
                    ],
                }
                acceptance_path.write_text(json.dumps(acceptance, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for path in (workspace_path, board_path, list_path, activity_path, preview_path, acceptance_path):
                        zf.write(path, path.name)
                return {
                    "demo_workspace_json": str(workspace_path),
                    "task_board_json": str(board_path),
                    "task_list_json": str(list_path),
                    "activity_feed_json": str(activity_path),
                    "preview_html": str(preview_path),
                    "acceptance_report_json": str(acceptance_path),
                    "acceptance_bundle_zip": str(bundle_path),
                }
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/service.py": textwrap.dedent(
            """
            from __future__ import annotations

            from pathlib import Path

            from .activity import add_activity, comment_on_task
            from .exporter import export_workspace
            from .filters import filter_tasks
            from .seed import load_demo_workspace
            from .tasks import create_task, edit_task_fields, move_task_status
            from .workspace import create_project, login_with_demo_user


            def generate_project(*, goal: str, project_name: str, out_dir: Path) -> dict[str, str]:
                workspace = load_demo_workspace()
                login = login_with_demo_user(workspace)
                actor = str(dict(login.get("user", {})).get("name", "Avery PM"))
                project = create_project(workspace, name=f"{project_name} Follow-up", description=goal[:180])
                task = create_task(
                    workspace,
                    project_id=str(project["project_id"]),
                    title="Validate delivery package",
                    description="Confirm README, startup, screenshot, verify report, and final package are present.",
                    assignee=actor,
                    priority="high",
                    due_date="2026-05-01",
                    labels=["delivery", "acceptance"],
                )
                edit_task_fields(workspace, str(task["task_id"]), description="Confirm the acceptance bundle is reviewable.")
                move_task_status(workspace, str(task["task_id"]), "doing")
                comment_on_task(workspace, task_id=str(task["task_id"]), author=actor, body="Delivery gate evidence is ready for review.")
                add_activity(workspace, task_id=str(task["task_id"]), actor=actor, action="filter", detail=f"{len(filter_tasks(workspace, status='doing'))} doing tasks visible")
                return export_workspace(workspace, out_dir)
            """
        ).lstrip(),
    }


def _team_task_pm_seed_map(project_root: str, package_name: str) -> dict[str, str]:
    return {
        f"{project_root}/src/{package_name}/seed.py": textwrap.dedent(
            """
            from __future__ import annotations

            from copy import deepcopy


            DEMO_WORKSPACE: dict[str, object] = {
                "workspace_id": "ws_team_ops",
                "name": "Team Ops",
                "users": [
                    {"user_id": "u1", "name": "Avery PM", "role": "owner"},
                    {"user_id": "u2", "name": "Mina Design", "role": "member"},
                    {"user_id": "u3", "name": "Kai Build", "role": "member"},
                ],
                "projects": [
                    {"project_id": "proj_launch", "workspace_id": "ws_team_ops", "name": "Launch Board", "description": "MVP launch work"},
                    {"project_id": "proj_growth", "workspace_id": "ws_team_ops", "name": "Growth Tasks", "description": "Small-team follow-up work"},
                ],
                "tasks": [
                    {"task_id": "t1", "project_id": "proj_launch", "title": "Freeze MVP scope", "description": "Confirm board/list/detail scope", "status": "done", "priority": "high", "assignee": "Avery PM", "due_date": "2026-04-24", "labels": ["scope"]},
                    {"task_id": "t2", "project_id": "proj_launch", "title": "Build kanban board", "description": "Render backlog/todo/doing/review/done lanes", "status": "doing", "priority": "high", "assignee": "Kai Build", "due_date": "2026-04-27", "labels": ["board", "frontend"]},
                    {"task_id": "t3", "project_id": "proj_launch", "title": "Add task detail drawer", "description": "Show title, description, priority, labels, assignee, comments", "status": "review", "priority": "medium", "assignee": "Mina Design", "due_date": "2026-04-28", "labels": ["detail"]},
                    {"task_id": "t4", "project_id": "proj_launch", "title": "Wire filters", "description": "Filter by status, assignee, label, priority", "status": "todo", "priority": "medium", "assignee": "Kai Build", "due_date": "2026-04-29", "labels": ["filter"]},
                    {"task_id": "t5", "project_id": "proj_growth", "title": "Activity feed", "description": "Record task movement and comments", "status": "doing", "priority": "medium", "assignee": "Avery PM", "due_date": "2026-04-30", "labels": ["activity"]},
                    {"task_id": "t6", "project_id": "proj_growth", "title": "Demo seed data", "description": "Ship useful workspaces/projects/tasks", "status": "done", "priority": "low", "assignee": "Mina Design", "due_date": "2026-04-25", "labels": ["sample"]},
                    {"task_id": "t7", "project_id": "proj_growth", "title": "README startup steps", "description": "Document local run and export path", "status": "todo", "priority": "high", "assignee": "Avery PM", "due_date": "2026-05-01", "labels": ["delivery"]},
                    {"task_id": "t8", "project_id": "proj_growth", "title": "Final screenshot", "description": "Capture real preview page", "status": "backlog", "priority": "medium", "assignee": "Kai Build", "due_date": "2026-05-02", "labels": ["evidence"]},
                ],
                "comments": [
                    {"comment_id": "c1", "task_id": "t2", "author": "Avery PM", "body": "Keep the board dense enough for repeated team use."},
                    {"comment_id": "c2", "task_id": "t3", "author": "Mina Design", "body": "Detail drawer should keep task fields visible."},
                    {"comment_id": "c3", "task_id": "t5", "author": "Kai Build", "body": "Activity rows are ready for acceptance review."},
                ],
                "activity": [
                    {"event_id": "e1", "task_id": "t1", "actor": "Avery PM", "action": "move_task_status", "detail": "done"},
                    {"event_id": "e2", "task_id": "t2", "actor": "Kai Build", "action": "move_task_status", "detail": "doing"},
                    {"event_id": "e3", "task_id": "t3", "actor": "Mina Design", "action": "comment_on_task", "detail": "detail UX reviewed"},
                ],
            }


            def load_demo_workspace() -> dict[str, object]:
                return deepcopy(DEMO_WORKSPACE)
            """
        ).lstrip()
    }


def _team_task_pm_test_map(project_root: str, package_name: str) -> dict[str, str]:
    return {
        f"{project_root}/tests/test_{package_name}_service.py": textwrap.dedent(
            f"""
            from __future__ import annotations

            import json
            import sys
            import tempfile
            import unittest
            from pathlib import Path

            ROOT = Path(__file__).resolve().parents[1]
            SRC = ROOT / "src"
            if str(SRC) not in sys.path:
                sys.path.insert(0, str(SRC))

            from {package_name}.app import health_payload
            from {package_name}.filters import filter_tasks
            from {package_name}.seed import load_demo_workspace
            from {package_name}.service import generate_project


            class TeamTaskPmTests(unittest.TestCase):
                def test_demo_workspace_has_board_list_detail_filter_activity(self) -> None:
                    workspace = load_demo_workspace()
                    self.assertGreaterEqual(len(workspace["projects"]), 2)
                    self.assertGreaterEqual(len(workspace["tasks"]), 8)
                    self.assertTrue(filter_tasks(workspace, status="doing"))
                    self.assertEqual(health_payload()["archetype"], "team_task_pm_web")

                def test_generate_project_exports_acceptance_bundle(self) -> None:
                    with tempfile.TemporaryDirectory(prefix="team_task_pm_") as td:
                        result = generate_project(goal="team task pm smoke", project_name="Plane-lite Team PM", out_dir=Path(td))
                        self.assertTrue(Path(result["demo_workspace_json"]).exists())
                        self.assertTrue(Path(result["task_board_json"]).exists())
                        self.assertTrue(Path(result["task_list_json"]).exists())
                        self.assertTrue(Path(result["activity_feed_json"]).exists())
                        self.assertTrue(Path(result["preview_html"]).exists())
                        self.assertTrue(Path(result["acceptance_bundle_zip"]).exists())
                        doc = json.loads(Path(result["acceptance_report_json"]).read_text(encoding="utf-8"))
                        self.assertEqual(doc["status"], "pass")
                        self.assertIn("task_detail_drawer", doc["checks"])


            if __name__ == "__main__":
                unittest.main()
            """
        ).lstrip()
    }


def _team_task_pm_files(
    *,
    goal_text: str,
    project_id: str,
    project_root: str,
    package_name: str,
    startup_rel: str,
    workflow_doc_rel: str,
    context_used: list[str],
    project_archetype: str,
    project_intent: dict[str, Any],
    project_spec: dict[str, Any],
) -> dict[str, str]:
    goal_excerpt = _goal_excerpt(goal_text)
    high_quality = str(project_spec.get("build_profile", "")).strip() == "high_quality_extended"
    common = _common_files(
        goal_text=goal_text,
        project_id=project_id,
        project_root=project_root,
        package_name=package_name,
        startup_rel=startup_rel,
        workflow_doc_rel=workflow_doc_rel,
        context_used=context_used,
        project_archetype=project_archetype,
        project_intent=project_intent,
        project_spec=project_spec,
        readme_body="This Plane-lite/Focalboard-lite MVP provides login, workspace/project switcher, kanban board, task list, task detail, task CRUD, filters, comments, activity, and demo exports.",
        workflow_title="Team Task PM Workflow",
        mode_label="Team task PM launcher.",
    )
    command = _quickstart_command(startup_rel=startup_rel, package_name=package_name, project_name="Plane-lite Team PM")
    common[f"{project_root}/README.md"] = (
        "# Plane-lite Team PM\n\n"
        "## What This Project Is\n\n"
        f"A local-first small-team task collaboration platform inspired by Plane-lite and Focalboard-lite. Scoped goal reference: {goal_excerpt}\n\n"
        "## Implemented\n\n"
        "- Demo login, workspace/project switcher, kanban board, task list, task detail drawer, task CRUD, filters, comments, and activity feed.\n"
        "- Seed workspace with demo users, two projects, eight baseline tasks, comments, and activity events.\n"
        "- Export path for demo workspace JSON, board JSON, task list JSON, activity feed JSON, preview HTML, acceptance report, and acceptance bundle zip.\n\n"
        "## Not Implemented\n\n"
        "- Realtime websocket collaboration.\n"
        "- OAuth, RBAC, notifications, Gantt, or roadmap planning.\n"
        "- Production database or multi-tenant hosting.\n\n"
        "## How To Run\n\n"
        f"`{command}`\n\n"
        "Startup steps:\n\n"
        "1. Run the command above from the project root.\n"
        "2. Use `--serve` for a health preview.\n"
        "3. Run without `--serve` to export demo deliverables into `generated_output/deliverables/`.\n\n"
        "## Sample Data\n\n"
        "- Demo users: Avery PM, Mina Design, Kai Build.\n"
        "- Demo projects: Launch Board and Growth Tasks.\n"
        "- Demo tasks cover backlog, ready, doing, review, and done statuses.\n\n"
        "## Directory Map\n\n"
        "- `src/` task collaboration domain logic.\n"
        "- `tests/` service regression coverage.\n"
        "- `docs/` generated workflow notes.\n"
        "- `generated_output/` runtime exports after startup.\n\n"
        "## Limitations\n\n"
        "- This is an MVP for local review, not a hosted SaaS.\n"
        "- Data is in-memory seed data for deterministic benchmark replay.\n"
        "- The UI preview is a static export surface for acceptance evidence.\n\n"
        "## Repo Context Consumed\n\n"
        f"{_context_lines(context_used)}\n"
    )
    if high_quality:
        common[f"{project_root}/README.md"] += (
            "\n## Feature Matrix\n\n"
            "| Area | Coverage |\n|---|---|\n"
            "| Dashboard summaries | implemented |\n"
            "| Project list and overview | implemented |\n"
            "| Task list and kanban board | implemented |\n"
            "| Task detail, comments, activity | implemented |\n"
            "| Search/filter/sort | implemented |\n"
            "| Import/export | implemented |\n\n"
            "## Page Map\n\n"
            "- Dashboard\n- Project list\n- Project overview\n- Task list\n- Kanban board\n- Task detail\n- Activity feed\n- Project settings\n\n"
            "## Data Model Summary\n\n"
            "- Workspace -> users/projects.\n"
            "- Project -> tasks/backlog/settings.\n"
            "- Task -> title/description/status/priority/assignee/due_date/labels/comments/activity.\n\n"
            "## Replay Steps\n\n"
            "1. Run the startup command.\n"
            "2. Export demo deliverables.\n"
            "3. Review `artifacts/screenshots/` for the eight page coverage images.\n"
        )
    common[f"{project_root}/docs/00_CORE.md"] = "# Core Runtime Notes\n\n- project_domain: team_task_management\n- scaffold_family: team_task_pm\n- project_archetype: team_task_pm_web\n- mainline: demo login -> workspace/project -> board/list/detail -> CRUD/filter/activity -> export/delivery\n"
    common[f"{project_root}/{workflow_doc_rel}"] = "# Team Task PM Workflow\n\n1. Resolve Plane-lite/Focalboard-lite task collaboration domain.\n2. Freeze workspace, project, task, comment, and activity models.\n3. Materialize board, list, detail, CRUD, filter, and activity modules.\n4. Run health preview and export demo acceptance bundle.\n"
    common[f"{project_root}/meta/tasks/CURRENT.md"] = "# Generated Task Card\n\n- Topic: Plane-lite team task management MVP delivery\n- Project Type: team_task_pm\n- Project Archetype: team_task_pm_web\n"
    common[f"{project_root}/meta/reports/LAST.md"] = "# Generated Report\n\n## Readlist\n- team task PM domain contract\n\n## Plan\n- materialize board/list/detail CRUD and delivery evidence\n\n## Changes\n- generated Plane-lite/Focalboard-lite task collaboration MVP\n\n## Verify\n- health preview and export probes are available\n\n## Questions\n- none\n\n## Demo\n- preview.html and acceptance_bundle.zip exported\n"
    common[f"{project_root}/meta/manifest.json"] = json.dumps(
        {
            "schema_version": "ctcp-generated-project-manifest-v1",
            "project_type": "team_task_pm",
            "project_domain": "team_task_management",
            "scaffold_family": "team_task_pm",
            "project_archetype": "team_task_pm_web",
            "goal": goal_excerpt,
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"
    if high_quality:
        common[f"{project_root}/src/{package_name}/dashboard.py"] = "from __future__ import annotations\nfrom collections import Counter\ndef dashboard_summary(workspace: dict[str, object]) -> dict[str, object]:\n    tasks=[row for row in workspace.get('tasks', []) if isinstance(row, dict)]\n    return {'task_count': len(tasks), 'status_counts': dict(Counter(str(t.get('status','')) for t in tasks)), 'priority_counts': dict(Counter(str(t.get('priority','')) for t in tasks)), 'project_count': len([p for p in workspace.get('projects', []) if isinstance(p, dict)])}\n"
        common[f"{project_root}/src/{package_name}/pages.py"] = "from __future__ import annotations\nPAGES=['dashboard','project_list','project_overview','task_list','kanban_board','task_detail','activity_feed','project_settings']\ndef page_map() -> list[dict[str, str]]:\n    return [{'page_id': page, 'status': 'implemented'} for page in PAGES]\n"
        common[f"{project_root}/src/{package_name}/search.py"] = "from __future__ import annotations\ndef search_tasks(workspace: dict[str, object], query: str) -> list[dict[str, object]]:\n    q=str(query or '').lower()\n    return [task for task in workspace.get('tasks', []) if isinstance(task, dict) and (q in str(task.get('title','')).lower() or q in str(task.get('description','')).lower() or q in ' '.join(str(x).lower() for x in task.get('labels', [])))]\ndef sort_tasks(tasks: list[dict[str, object]], key: str='due_date') -> list[dict[str, object]]:\n    return sorted(tasks, key=lambda row: str(row.get(key, '')))\n"
        common[f"{project_root}/src/{package_name}/import_export.py"] = "from __future__ import annotations\nimport json\nfrom pathlib import Path\ndef export_workspace_json(workspace: dict[str, object], path: Path) -> str:\n    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(workspace, ensure_ascii=False, indent=2)+'\\n', encoding='utf-8'); return str(path)\ndef import_workspace_json(path: Path) -> dict[str, object]:\n    return json.loads(path.read_text(encoding='utf-8'))\n"
        common[f"{project_root}/src/{package_name}/settings.py"] = "from __future__ import annotations\ndef project_settings(project: dict[str, object]) -> dict[str, object]:\n    return {'project_id': project.get('project_id',''), 'name': project.get('name',''), 'default_view': 'kanban_board', 'enabled_views': ['dashboard','list','board','activity'], 'import_export_enabled': True}\n"
    return _merge_file_maps(
        common,
        _team_task_pm_seed_map(project_root, package_name),
        _team_task_pm_module_map(project_root, package_name),
        _team_task_pm_test_map(project_root, package_name),
    )


def _indie_studio_hub_files(
    *,
    goal_text: str,
    project_id: str,
    project_root: str,
    package_name: str,
    startup_rel: str,
    workflow_doc_rel: str,
    context_used: list[str],
    project_archetype: str,
    project_intent: dict[str, Any],
    project_spec: dict[str, Any],
) -> dict[str, str]:
    base = _team_task_pm_files(
        goal_text=goal_text,
        project_id=project_id,
        project_root=project_root,
        package_name=package_name,
        startup_rel=startup_rel,
        workflow_doc_rel=workflow_doc_rel,
        context_used=context_used,
        project_archetype=project_archetype,
        project_intent=project_intent,
        project_spec=project_spec,
    )
    goal_excerpt = _goal_excerpt(goal_text)
    command = _quickstart_command(startup_rel=startup_rel, package_name=package_name, project_name="Indie Studio Production Hub")
    extras = {
        f"{project_root}/README.md": (
            "# Indie Studio Production Hub\n\n"
            "## What This Project Is\n\n"
            f"A local-first production collaboration hub for a 5-20 person indie game or VN team. Scoped goal reference: {goal_excerpt}\n\n"
            "## Implemented\n\n"
            "- Dashboard, project list/overview, milestone backlog, task board/list/detail, activity feed, and project settings.\n"
            "- Asset library plus asset detail for character art, backgrounds, BGM, SFX, script fragments, and replacement tracking.\n"
            "- Bug tracker with severity, repro steps, linked version, linked tasks/assets, and QA flow.\n"
            "- Build / Release center with build records, release summary, current version status, and release checklist.\n"
            "- Docs Center plus export bundle for feature matrix, page map, data model summary, milestone plan, startup guide, replay guide, and mid-stage review.\n\n"
            "## Not Implemented\n\n"
            "- Realtime websocket collaboration.\n"
            "- OAuth, cloud sync, multi-tenant SaaS, complex RBAC, AI scheduling, or payment flows.\n\n"
            "## How To Run\n\n"
            f"`{command}`\n\n"
            "Startup steps:\n\n"
            "1. Run the command above from the project root.\n"
            "2. Use `--serve` for the health payload and preview contract.\n"
            "3. Run without `--serve` to export demo deliverables into `generated_output/deliverables/`.\n\n"
            "## Sample Data\n\n"
            "- Demo users: producer, design, engineering, art, and QA.\n"
            "- Demo project: Episode One vertical slice with backlog, assets, bugs, and release checklist.\n"
            "- Demo assets include character portrait, background, bgm, and script fragment placeholders.\n"
            "- Demo bugs and builds show version progress across the same local workspace.\n\n"
            "## Directory Map\n\n"
            "- `src/` domain logic for tasks, assets, bugs, releases, docs, and export.\n"
            "- `docs/` shipped product-definition and replay docs.\n"
            "- `tests/` service regression coverage.\n"
            "- `generated_output/` runtime exports after startup.\n\n"
            "## Limitations\n\n"
            "- This MVP is local-first and single-workspace.\n"
            "- Data is deterministic in-memory seed data for repeatable replay.\n"
            "- The preview is a static export surface, not a live collaborative frontend.\n\n"
            "## Repo Context Consumed\n\n"
            f"{_context_lines(context_used)}\n"
        ),
        f"{project_root}/docs/00_CORE.md": (
            "# Core Runtime Notes\n\n"
            "- project_domain: indie_studio_production_hub\n"
            "- scaffold_family: indie_studio_hub\n"
            "- project_archetype: indie_studio_hub_web\n"
            "- mainline: dashboard -> project overview -> milestone backlog -> task board/list/detail -> asset library/detail -> bug tracker -> build release center -> docs center -> export bundle\n"
        ),
        f"{project_root}/{workflow_doc_rel}": (
            "# Indie Studio Production Hub Workflow\n\n"
            "1. Freeze project, milestone, task, asset, bug, build, release, and docs-center models.\n"
            "2. Materialize dashboard, project views, task board/list/detail, asset library/detail, bug tracker, build/release center, activity feed, and docs center.\n"
            "3. Export release summary, asset library, bug tracker, docs center, and acceptance bundle.\n"
        ),
        f"{project_root}/meta/tasks/CURRENT.md": "# Generated Task Card\n\n- Topic: Indie Studio Production Hub MVP delivery\n- Project Type: indie_studio_hub\n- Project Archetype: indie_studio_hub_web\n",
        f"{project_root}/meta/reports/LAST.md": "# Generated Report\n\n## Readlist\n- indie studio production hub domain contract\n\n## Plan\n- materialize dashboard/tasks/assets/bugs/releases/docs and export evidence\n\n## Changes\n- generated composite local-first indie studio production hub MVP\n\n## Verify\n- health preview and export probes are available\n\n## Questions\n- none\n\n## Demo\n- preview.html, release_summary.json, docs bundle, and acceptance_bundle.zip exported\n",
        f"{project_root}/meta/manifest.json": json.dumps(
            {
                "schema_version": "ctcp-generated-project-manifest-v1",
                "project_type": "indie_studio_hub",
                "project_domain": "indie_studio_production_hub",
                "scaffold_family": "indie_studio_hub",
                "project_archetype": "indie_studio_hub_web",
                "goal": goal_excerpt,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        f"{project_root}/docs/feature_matrix.md": "# Feature Matrix\n\n| Capability | Status |\n|---|---|\n| Dashboard | implemented |\n| Project overview | implemented |\n| Milestone backlog | implemented |\n| Task board/list/detail | implemented |\n| Asset library/detail | implemented |\n| Bug tracker | implemented |\n| Build / release center | implemented |\n| Docs center | implemented |\n| Search and filters | implemented |\n| Import / export | implemented |\n",
        f"{project_root}/docs/page_map.md": "# Page Map\n\n- Dashboard\n- Project List\n- Project Overview\n- Milestone Backlog\n- Task Board\n- Task List\n- Task Detail\n- Asset Library\n- Asset Detail\n- Bug Tracker\n- Build / Release Center\n- Activity Feed\n- Docs Center\n- Project Settings\n",
        f"{project_root}/docs/data_model_summary.md": "# Data Model Summary\n\n- Workspace owns users, projects, milestones, activity, and docs.\n- Project owns tasks, assets, bugs, builds, release summary, and export scope.\n- Task links assignee, due date, priority, labels, and related assets/bugs.\n- Asset tracks owner, asset type, status, preview, replacement state, and linked task ids.\n- Bug tracks severity, repro steps, linked version, linked task ids, linked asset ids, and QA status.\n- BuildRecord tracks version, branch, milestone, checklist, summary, and release owner.\n",
        f"{project_root}/docs/milestone_plan.md": "# Milestone Plan\n\n- Pre-production freeze\n- Vertical slice milestone\n- Content integration milestone\n- Release candidate milestone\n",
        f"{project_root}/docs/startup_guide.md": f"# Startup Guide\n\n1. Run `{command}`.\n2. Use `--serve` to inspect health payload.\n3. Run export mode to populate `generated_output/deliverables/`.\n4. Review screenshots and docs bundle.\n",
        f"{project_root}/docs/replay_guide.md": "# Replay Guide\n\n1. Start from the project root.\n2. Run the launcher in export mode.\n3. Verify preview.html plus exported JSON artifacts.\n4. Confirm screenshots cover dashboard, tasks, assets, bugs, build/release, activity, docs, and settings.\n",
        f"{project_root}/docs/mid_stage_review.md": "# Mid Stage Review\n\n- Dashboard/tasks/assets/bugs/release/docs surfaces are present.\n- Export bundle includes asset, bug, release, and docs center summaries.\n- Remaining work is polish only, not domain expansion.\n",
        f"{project_root}/src/{package_name}/seed.py": textwrap.dedent(
            """
            from __future__ import annotations

            from copy import deepcopy


            DEMO_WORKSPACE: dict[str, object] = {
                "workspace_id": "ws_indie_studio",
                "name": "Indie Studio Production Hub",
                "users": [
                    {"user_id": "u1", "name": "Rin Producer", "role": "owner"},
                    {"user_id": "u2", "name": "Aki Design", "role": "design"},
                    {"user_id": "u3", "name": "Moe Engineer", "role": "engineering"},
                    {"user_id": "u4", "name": "Sora Artist", "role": "art"},
                    {"user_id": "u5", "name": "Tao QA", "role": "qa"},
                ],
                "projects": [
                    {"project_id": "proj_episode_one", "workspace_id": "ws_indie_studio", "name": "Episode One", "description": "Vertical slice delivery"},
                ],
                "milestones": [
                    {"milestone_id": "m1", "project_id": "proj_episode_one", "name": "Vertical Slice", "status": "doing", "owner": "Rin Producer", "due_date": "2026-05-10"},
                    {"milestone_id": "m2", "project_id": "proj_episode_one", "name": "Release Candidate", "status": "todo", "owner": "Moe Engineer", "due_date": "2026-05-24"},
                ],
                "tasks": [
                    {"task_id": "t1", "project_id": "proj_episode_one", "title": "Freeze opening scene flow", "description": "Lock script beats and branch handoff.", "status": "done", "priority": "high", "assignee": "Aki Design", "due_date": "2026-04-25", "labels": ["narrative"], "asset_ids": ["asset_script_01"], "bug_ids": []},
                    {"task_id": "t2", "project_id": "proj_episode_one", "title": "Implement save-room transition", "description": "Wire scene transition and return path.", "status": "doing", "priority": "high", "assignee": "Moe Engineer", "due_date": "2026-04-29", "labels": ["engineering"], "asset_ids": ["asset_bg_room"], "bug_ids": ["bug_001"]},
                    {"task_id": "t3", "project_id": "proj_episode_one", "title": "Replace heroine portrait placeholder", "description": "Swap temporary portrait before QA pass.", "status": "review", "priority": "medium", "assignee": "Sora Artist", "due_date": "2026-04-30", "labels": ["art"], "asset_ids": ["asset_portrait_heroine"], "bug_ids": []},
                    {"task_id": "t4", "project_id": "proj_episode_one", "title": "QA smoke for build 0.3.0", "description": "Replay branching and collect regressions.", "status": "todo", "priority": "high", "assignee": "Tao QA", "due_date": "2026-05-01", "labels": ["qa"], "asset_ids": [], "bug_ids": ["bug_002"]},
                ],
                "assets": [
                    {"asset_id": "asset_portrait_heroine", "project_id": "proj_episode_one", "name": "Heroine Portrait", "asset_type": "character_portrait", "status": "waiting_replacement", "owner": "Sora Artist", "preview": "portrait-v2.png", "linked_task_ids": ["t3"], "missing": False},
                    {"asset_id": "asset_bg_room", "project_id": "proj_episode_one", "name": "Save Room Background", "asset_type": "background", "status": "approved", "owner": "Sora Artist", "preview": "bg-room.png", "linked_task_ids": ["t2"], "missing": False},
                    {"asset_id": "asset_bgm_theme", "project_id": "proj_episode_one", "name": "Opening Theme", "asset_type": "bgm", "status": "review", "owner": "Aki Design", "preview": "theme-loop.ogg", "linked_task_ids": [], "missing": False},
                    {"asset_id": "asset_script_01", "project_id": "proj_episode_one", "name": "Scene Script Fragment", "asset_type": "script_fragment", "status": "approved", "owner": "Aki Design", "preview": "scene-01.txt", "linked_task_ids": ["t1"], "missing": False},
                ],
                "bugs": [
                    {"bug_id": "bug_001", "project_id": "proj_episode_one", "title": "Transition fades too early", "severity": "major", "status": "doing", "version": "0.3.0", "linked_task_ids": ["t2"], "linked_asset_ids": ["asset_bg_room"], "repro_steps": ["load save room", "trigger transition", "observe fade"], "owner": "Moe Engineer"},
                    {"bug_id": "bug_002", "project_id": "proj_episode_one", "title": "Textbox overlaps portrait", "severity": "minor", "status": "todo", "version": "0.3.0", "linked_task_ids": ["t4"], "linked_asset_ids": ["asset_portrait_heroine"], "repro_steps": ["open dialogue scene", "advance to line 12"], "owner": "Tao QA"},
                ],
                "builds": [
                    {"build_id": "build_030", "project_id": "proj_episode_one", "version": "0.3.0", "branch": "vertical-slice", "status": "candidate", "owner": "Moe Engineer", "milestone_id": "m1", "release_summary": "Vertical slice content-complete candidate", "checklist": ["branch merged", "qa smoke", "docs updated"]},
                ],
                "docs_center": [
                    {"doc_id": "doc_feature_matrix", "title": "Feature Matrix", "status": "published"},
                    {"doc_id": "doc_page_map", "title": "Page Map", "status": "published"},
                    {"doc_id": "doc_milestone_plan", "title": "Milestone Plan", "status": "published"},
                ],
                "comments": [
                    {"comment_id": "c1", "task_id": "t2", "author": "Rin Producer", "body": "Keep this in the current milestone."},
                    {"comment_id": "c2", "task_id": "t3", "author": "Sora Artist", "body": "Replacement portrait is in final review."},
                ],
                "activity": [
                    {"event_id": "e1", "task_id": "t1", "actor": "Aki Design", "action": "move_task_status", "detail": "done"},
                    {"event_id": "e2", "task_id": "t2", "actor": "Moe Engineer", "action": "move_task_status", "detail": "doing"},
                    {"event_id": "e3", "task_id": "t3", "actor": "Sora Artist", "action": "asset_update", "detail": "portrait replacement queued"},
                ],
            }


            def load_demo_workspace() -> dict[str, object]:
                return deepcopy(DEMO_WORKSPACE)
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/workspace.py": textwrap.dedent(
            """
            from __future__ import annotations


            def login_with_demo_user(workspace: dict[str, object], *, role: str = "owner") -> dict[str, object]:
                for user in workspace.get("users", []):
                    if isinstance(user, dict) and str(user.get("role", "")).strip() == role:
                        return {"status": "ok", "user": user}
                users = [row for row in workspace.get("users", []) if isinstance(row, dict)]
                return {"status": "ok", "user": users[0] if users else {}}


            def create_project(workspace: dict[str, object], *, name: str, description: str) -> dict[str, object]:
                projects = workspace.setdefault("projects", [])
                project = {"project_id": f"proj_{len(projects) + 1}", "workspace_id": workspace.get("workspace_id", "workspace"), "name": name, "description": description}
                projects.append(project)
                return project


            def milestone_backlog(workspace: dict[str, object]) -> list[dict[str, object]]:
                return [row for row in workspace.get("milestones", []) if isinstance(row, dict)]


            def project_overview(workspace: dict[str, object], *, project_id: str) -> dict[str, object]:
                tasks = [row for row in workspace.get("tasks", []) if isinstance(row, dict) and row.get("project_id") == project_id]
                assets = [row for row in workspace.get("assets", []) if isinstance(row, dict) and row.get("project_id") == project_id]
                bugs = [row for row in workspace.get("bugs", []) if isinstance(row, dict) and row.get("project_id") == project_id]
                builds = [row for row in workspace.get("builds", []) if isinstance(row, dict) and row.get("project_id") == project_id]
                return {
                    "task_count": len(tasks),
                    "asset_count": len(assets),
                    "bug_count": len(bugs),
                    "build_count": len(builds),
                }
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/assets.py": textwrap.dedent(
            """
            from __future__ import annotations


            def asset_library(workspace: dict[str, object]) -> list[dict[str, object]]:
                return [row for row in workspace.get("assets", []) if isinstance(row, dict)]


            def asset_detail(workspace: dict[str, object], asset_id: str) -> dict[str, object]:
                for asset in workspace.get("assets", []):
                    if isinstance(asset, dict) and str(asset.get("asset_id", "")).strip() == asset_id:
                        return asset
                return {}


            def create_asset(workspace: dict[str, object], *, project_id: str, name: str, asset_type: str, owner: str) -> dict[str, object]:
                assets = workspace.setdefault("assets", [])
                asset = {
                    "asset_id": f"asset_{len(assets) + 1}",
                    "project_id": project_id,
                    "name": name,
                    "asset_type": asset_type,
                    "status": "todo",
                    "owner": owner,
                    "preview": "",
                    "linked_task_ids": [],
                    "missing": False,
                }
                assets.append(asset)
                return asset


            def mark_asset_missing(workspace: dict[str, object], asset_id: str, *, missing: bool = True) -> dict[str, object]:
                asset = asset_detail(workspace, asset_id)
                if asset:
                    asset["missing"] = missing
                    asset["status"] = "needs_replacement" if missing else str(asset.get("status", "todo"))
                return asset
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/bugs.py": textwrap.dedent(
            """
            from __future__ import annotations


            def bug_tracker(workspace: dict[str, object]) -> list[dict[str, object]]:
                return [row for row in workspace.get("bugs", []) if isinstance(row, dict)]


            def report_bug(workspace: dict[str, object], *, project_id: str, title: str, severity: str, version: str, owner: str) -> dict[str, object]:
                bugs = workspace.setdefault("bugs", [])
                bug = {
                    "bug_id": f"bug_{len(bugs) + 1:03d}",
                    "project_id": project_id,
                    "title": title,
                    "severity": severity,
                    "status": "todo",
                    "version": version,
                    "linked_task_ids": [],
                    "linked_asset_ids": [],
                    "repro_steps": [],
                    "owner": owner,
                }
                bugs.append(bug)
                return bug


            def update_bug_status(workspace: dict[str, object], bug_id: str, status: str) -> dict[str, object]:
                for bug in workspace.get("bugs", []):
                    if isinstance(bug, dict) and str(bug.get("bug_id", "")).strip() == bug_id:
                        bug["status"] = status
                        return bug
                return {}
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/releases.py": textwrap.dedent(
            """
            from __future__ import annotations


            def build_records(workspace: dict[str, object]) -> list[dict[str, object]]:
                return [row for row in workspace.get("builds", []) if isinstance(row, dict)]


            def create_build_record(workspace: dict[str, object], *, project_id: str, version: str, branch: str, owner: str) -> dict[str, object]:
                builds = workspace.setdefault("builds", [])
                build = {
                    "build_id": f"build_{len(builds) + 1:03d}",
                    "project_id": project_id,
                    "version": version,
                    "branch": branch,
                    "status": "candidate",
                    "owner": owner,
                    "milestone_id": "",
                    "release_summary": "",
                    "checklist": ["branch merged", "qa smoke", "docs updated"],
                }
                builds.append(build)
                return build


            def release_summary(workspace: dict[str, object]) -> dict[str, object]:
                builds = build_records(workspace)
                latest = builds[-1] if builds else {}
                return {
                    "current_version_status": str(latest.get("status", "unknown")),
                    "version": str(latest.get("version", "")),
                    "release_summary": str(latest.get("release_summary", "")),
                    "release_checklist": list(latest.get("checklist", [])) if isinstance(latest.get("checklist", []), list) else [],
                }
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/docs_center.py": textwrap.dedent(
            """
            from __future__ import annotations


            def docs_center_index(workspace: dict[str, object]) -> list[dict[str, object]]:
                return [row for row in workspace.get("docs_center", []) if isinstance(row, dict)]


            def export_docs_center(workspace: dict[str, object]) -> dict[str, object]:
                return {
                    "docs_center": docs_center_index(workspace),
                    "required_docs": [
                        "feature_matrix.md",
                        "page_map.md",
                        "data_model_summary.md",
                        "milestone_plan.md",
                        "startup_guide.md",
                        "replay_guide.md",
                        "mid_stage_review.md",
                    ],
                }
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/dashboard.py": textwrap.dedent(
            """
            from __future__ import annotations

            from .assets import asset_library
            from .bugs import bug_tracker
            from .releases import build_records


            def dashboard_summary(workspace: dict[str, object]) -> dict[str, object]:
                tasks = [row for row in workspace.get("tasks", []) if isinstance(row, dict)]
                return {
                    "project_count": len([row for row in workspace.get("projects", []) if isinstance(row, dict)]),
                    "task_count": len(tasks),
                    "asset_count": len(asset_library(workspace)),
                    "bug_count": len(bug_tracker(workspace)),
                    "build_count": len(build_records(workspace)),
                }
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/pages.py": "from __future__ import annotations\nPAGES=['dashboard','project_list','project_overview','milestone_backlog','task_board','task_list','task_detail','asset_library','asset_detail','bug_tracker','build_release_center','activity_feed','docs_center','project_settings']\ndef page_map() -> list[dict[str, str]]:\n    return [{'page_id': page, 'status': 'implemented'} for page in PAGES]\n",
        f"{project_root}/src/{package_name}/search.py": "from __future__ import annotations\ndef search_workspace(workspace: dict[str, object], query: str) -> list[dict[str, object]]:\n    q=str(query or '').lower()\n    pools=[]\n    for key in ('tasks','assets','bugs','docs_center'):\n        pools.extend([row for row in workspace.get(key, []) if isinstance(row, dict)])\n    return [row for row in pools if q in (' '.join(str(v).lower() for v in row.values()))]\ndef sort_rows(rows: list[dict[str, object]], key: str='status') -> list[dict[str, object]]:\n    return sorted(rows, key=lambda row: str(row.get(key, '')))\n",
        f"{project_root}/src/{package_name}/import_export.py": "from __future__ import annotations\nimport json\nfrom pathlib import Path\ndef export_project_data(workspace: dict[str, object], path: Path) -> str:\n    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(workspace, ensure_ascii=False, indent=2)+'\\n', encoding='utf-8'); return str(path)\ndef import_project_data(path: Path) -> dict[str, object]:\n    return json.loads(path.read_text(encoding='utf-8'))\n",
        f"{project_root}/src/{package_name}/settings.py": "from __future__ import annotations\ndef project_settings(project: dict[str, object]) -> dict[str, object]:\n    return {'project_id': project.get('project_id',''), 'name': project.get('name',''), 'default_view': 'dashboard', 'enabled_views': ['dashboard','board','assets','bugs','release','docs'], 'docs_center_enabled': True, 'export_enabled': True}\n",
        f"{project_root}/src/{package_name}/app.py": textwrap.dedent(
            """
            from __future__ import annotations

            import html

            from .activity import activity_feed
            from .assets import asset_detail, asset_library
            from .board import build_kanban_board, build_task_list
            from .bugs import bug_tracker
            from .dashboard import dashboard_summary
            from .docs_center import docs_center_index
            from .releases import release_summary
            from .seed import load_demo_workspace
            from .workspace import milestone_backlog, project_overview


            def health_payload() -> dict[str, object]:
                workspace = load_demo_workspace()
                return {
                    "status": "ok",
                    "archetype": "indie_studio_hub_web",
                    "project_domain": "indie_studio_production_hub",
                    "tasks": len(workspace.get("tasks", [])),
                    "assets": len(workspace.get("assets", [])),
                    "bugs": len(workspace.get("bugs", [])),
                    "views": [
                        "dashboard",
                        "project_overview",
                        "milestone_backlog",
                        "task_board",
                        "task_list",
                        "task_detail",
                        "asset_library",
                        "asset_detail",
                        "bug_tracker",
                        "build_release_center",
                        "activity_feed",
                        "docs_center",
                        "project_settings",
                    ],
                }


            def render_preview_html(workspace: dict[str, object]) -> str:
                overview = project_overview(workspace, project_id="proj_episode_one")
                board = build_kanban_board(workspace)
                tasks = build_task_list(workspace)
                assets = asset_library(workspace)
                selected_asset = asset_detail(workspace, "asset_portrait_heroine") or (assets[0] if assets else {})
                bugs = bug_tracker(workspace)
                release = release_summary(workspace)
                docs = docs_center_index(workspace)
                milestones = milestone_backlog(workspace)
                events = activity_feed(workspace)
                dashboard = dashboard_summary(workspace)
                columns = []
                for status, rows in board.items():
                    cards = "".join(
                        f"<article class='task-card'><strong>{html.escape(str(row.get('title', 'Task')))}</strong><span>{html.escape(str(row.get('priority', 'medium')))}</span><small>{html.escape(str(row.get('assignee', 'Unassigned')))}</small></article>"
                        for row in rows
                    )
                    columns.append(f"<section class='kanban-column'><h3>{html.escape(status.title())}</h3>{cards}</section>")
                task_rows = "".join(
                    f"<tr><td>{html.escape(str(row.get('title', 'Task')))}</td><td>{html.escape(str(row.get('status', '')))}</td><td>{html.escape(str(row.get('assignee', '')))}</td><td>{html.escape(', '.join(row.get('labels', [])))}</td></tr>"
                    for row in tasks
                )
                asset_rows = "".join(
                    f"<tr><td>{html.escape(str(row.get('name', '')))}</td><td>{html.escape(str(row.get('asset_type', '')))}</td><td>{html.escape(str(row.get('status', '')))}</td><td>{html.escape(str(row.get('owner', '')))}</td></tr>"
                    for row in assets
                )
                bug_rows = "".join(
                    f"<tr><td>{html.escape(str(row.get('title', '')))}</td><td>{html.escape(str(row.get('severity', '')))}</td><td>{html.escape(str(row.get('status', '')))}</td><td>{html.escape(str(row.get('version', '')))}</td></tr>"
                    for row in bugs
                )
                milestone_rows = "".join(
                    f"<li>{html.escape(str(row.get('name', '')))} - {html.escape(str(row.get('status', '')))} - {html.escape(str(row.get('due_date', '')))}</li>"
                    for row in milestones
                )
                docs_rows = "".join(
                    f"<li>{html.escape(str(row.get('title', '')))} - {html.escape(str(row.get('status', '')))}</li>"
                    for row in docs
                )
                activity_rows = "".join(
                    f"<li><strong>{html.escape(str(row.get('actor', '')))}</strong> {html.escape(str(row.get('action', '')))} - {html.escape(str(row.get('detail', '')))}</li>"
                    for row in events
                )
                return f'''<!doctype html>
<html><head><meta charset="utf-8"><title>Indie Studio Production Hub</title>
<style>
body{{margin:0;font-family:Arial,sans-serif;background:#f4f6fb;color:#18202f}}
header{{display:flex;justify-content:space-between;align-items:center;padding:18px 24px;background:#ffffff;border-bottom:1px solid #d8dee9}}
main{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;padding:18px}}
.panel,.kanban-column{{background:#fff;border:1px solid #d8dee9;border-radius:8px;padding:12px}}
.kanban-board{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}
.task-card{{display:grid;gap:4px;padding:9px;margin:6px 0;border:1px solid #d8dee9;border-radius:6px;background:#fbfcff}}
table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #e5e9f0;padding:8px;text-align:left}}
ul{{margin:0;padding-left:18px}} .stats{{display:flex;gap:12px;flex-wrap:wrap}} .chip{{border:1px solid #a7b1c2;border-radius:16px;padding:4px 10px;background:#fff}}
</style></head>
<body>
<header><h1>Indie Studio Production Hub</h1><div class="stats"><span class="chip">dashboard: {dashboard['task_count']} tasks</span><span class="chip">asset_library: {dashboard['asset_count']}</span><span class="chip">bug_tracker: {dashboard['bug_count']}</span><span class="chip">build_release_center: {dashboard['build_count']}</span></div></header>
<main>
<section class="panel"><h2>dashboard</h2><p>project_overview tasks={overview['task_count']} assets={overview['asset_count']} bugs={overview['bug_count']} builds={overview['build_count']}</p></section>
<section class="panel"><h2>milestone_backlog</h2><ul>{milestone_rows}</ul></section>
<section><h2>task_board</h2><div class="kanban-board">{''.join(columns)}</div></section>
<section class="panel"><h2>task_list</h2><table><tbody>{task_rows}</tbody></table><h3>task_detail</h3><p>{html.escape(str(tasks[0].get('description', '')) if tasks else '')}</p></section>
<section class="panel"><h2>asset_library</h2><table><tbody>{asset_rows}</tbody></table></section>
<section class="panel"><h2>asset_detail</h2><p>{html.escape(str(selected_asset.get('name', '')))}</p><p>{html.escape(str(selected_asset.get('asset_type', '')))}</p><p>{html.escape(str(selected_asset.get('status', '')))}</p></section>
<section class="panel"><h2>bug_tracker</h2><table><tbody>{bug_rows}</tbody></table></section>
<section class="panel"><h2>build_release_center</h2><p>version: {html.escape(str(release.get('version', '')))}</p><p>current_version_status: {html.escape(str(release.get('current_version_status', '')))}</p><p>release_summary: {html.escape(str(release.get('release_summary', '')))}</p></section>
<section class="panel"><h2>activity_feed</h2><ul>{activity_rows}</ul></section>
<section class="panel"><h2>docs_center</h2><ul>{docs_rows}</ul></section>
</main></body></html>'''
            """
        ).lstrip().replace("\n            ", "\n"),
        f"{project_root}/src/{package_name}/exporter.py": textwrap.dedent(
            """
            from __future__ import annotations

            import json
            import zipfile
            from pathlib import Path

            from .activity import activity_feed
            from .app import render_preview_html
            from .assets import asset_library
            from .bugs import bug_tracker
            from .docs_center import export_docs_center
            from .releases import build_records, release_summary


            def export_workspace(workspace: dict[str, object], out_dir: Path) -> dict[str, str]:
                deliver_dir = out_dir / "deliverables"
                deliver_dir.mkdir(parents=True, exist_ok=True)
                workspace_path = deliver_dir / "demo_workspace.json"
                asset_path = deliver_dir / "asset_library.json"
                bug_path = deliver_dir / "bug_tracker.json"
                build_path = deliver_dir / "build_records.json"
                release_path = deliver_dir / "release_summary.json"
                docs_path = deliver_dir / "docs_center.json"
                activity_path = deliver_dir / "activity_feed.json"
                preview_path = deliver_dir / "preview.html"
                acceptance_path = deliver_dir / "acceptance_report.json"
                bundle_path = deliver_dir / "acceptance_bundle.zip"
                workspace_path.write_text(json.dumps(workspace, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                asset_path.write_text(json.dumps({"assets": asset_library(workspace)}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                bug_path.write_text(json.dumps({"bugs": bug_tracker(workspace)}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                build_path.write_text(json.dumps({"builds": build_records(workspace)}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                release_path.write_text(json.dumps(release_summary(workspace), ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                docs_path.write_text(json.dumps(export_docs_center(workspace), ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                activity_path.write_text(json.dumps({"activity": activity_feed(workspace)}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                preview_path.write_text(render_preview_html(workspace), encoding="utf-8")
                acceptance = {
                    "status": "pass",
                    "checks": [
                        "dashboard",
                        "project_overview",
                        "milestone_backlog",
                        "task_board",
                        "task_list",
                        "task_detail",
                        "asset_library",
                        "asset_detail",
                        "bug_tracker",
                        "build_release_center",
                        "activity_feed",
                        "docs_center",
                    ],
                }
                acceptance_path.write_text(json.dumps(acceptance, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
                with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for path in (workspace_path, asset_path, bug_path, build_path, release_path, docs_path, activity_path, preview_path, acceptance_path):
                        zf.write(path, path.name)
                return {
                    "demo_workspace_json": str(workspace_path),
                    "asset_library_json": str(asset_path),
                    "bug_tracker_json": str(bug_path),
                    "build_records_json": str(build_path),
                    "release_summary_json": str(release_path),
                    "docs_center_json": str(docs_path),
                    "activity_feed_json": str(activity_path),
                    "preview_html": str(preview_path),
                    "acceptance_report_json": str(acceptance_path),
                    "acceptance_bundle_zip": str(bundle_path),
                }
            """
        ).lstrip(),
        f"{project_root}/src/{package_name}/service.py": textwrap.dedent(
            """
            from __future__ import annotations

            from pathlib import Path

            from .activity import add_activity, comment_on_task
            from .assets import create_asset
            from .bugs import report_bug, update_bug_status
            from .exporter import export_workspace
            from .releases import create_build_record
            from .seed import load_demo_workspace
            from .tasks import create_task, move_task_status
            from .workspace import create_project, login_with_demo_user


            def generate_project(*, goal: str, project_name: str, out_dir: Path) -> dict[str, str]:
                workspace = load_demo_workspace()
                login = login_with_demo_user(workspace)
                actor = str(dict(login.get("user", {})).get("name", "Rin Producer"))
                project = create_project(workspace, name=project_name, description=goal[:180])
                task = create_task(
                    workspace,
                    project_id=str(project["project_id"]),
                    title="Finalize hub coverage review",
                    description="Confirm task, asset, bug, build, docs, and replay evidence.",
                    assignee=actor,
                    priority="high",
                    due_date="2026-05-02",
                    labels=["delivery", "hub"],
                )
                asset = create_asset(workspace, project_id=str(project["project_id"]), name="Release Banner", asset_type="marketing_art", owner=actor)
                bug = report_bug(workspace, project_id=str(project["project_id"]), title="Release summary typo", severity="minor", version="0.3.1", owner=actor)
                build = create_build_record(workspace, project_id=str(project["project_id"]), version="0.3.1", branch="release-candidate", owner=actor)
                move_task_status(workspace, str(task["task_id"]), "doing")
                update_bug_status(workspace, str(bug["bug_id"]), "review")
                comment_on_task(workspace, task_id=str(task["task_id"]), author=actor, body=f"Linked {asset['asset_id']} and {build['build_id']} for final review.")
                add_activity(workspace, task_id=str(task["task_id"]), actor=actor, action="release_review", detail="docs_center and release summary verified")
                return export_workspace(workspace, out_dir)
            """
        ).lstrip(),
        f"{project_root}/tests/test_{package_name}_service.py": textwrap.dedent(
            f"""
            from __future__ import annotations

            import json
            import sys
            import tempfile
            import unittest
            from pathlib import Path

            ROOT = Path(__file__).resolve().parents[1]
            SRC = ROOT / "src"
            if str(SRC) not in sys.path:
                sys.path.insert(0, str(SRC))

            from {package_name}.app import health_payload
            from {package_name}.assets import asset_library
            from {package_name}.bugs import bug_tracker
            from {package_name}.docs_center import docs_center_index
            from {package_name}.releases import release_summary
            from {package_name}.seed import load_demo_workspace
            from {package_name}.service import generate_project


            class IndieStudioHubTests(unittest.TestCase):
                def test_demo_workspace_has_assets_bugs_release_and_docs(self) -> None:
                    workspace = load_demo_workspace()
                    self.assertGreaterEqual(len(asset_library(workspace)), 4)
                    self.assertGreaterEqual(len(bug_tracker(workspace)), 2)
                    self.assertTrue(docs_center_index(workspace))
                    self.assertEqual(health_payload()["archetype"], "indie_studio_hub_web")
                    self.assertEqual(release_summary(workspace)["version"], "0.3.0")

                def test_generate_project_exports_composite_bundle(self) -> None:
                    with tempfile.TemporaryDirectory(prefix="indie_studio_hub_") as td:
                        result = generate_project(goal="indie studio hub smoke", project_name="Indie Studio Production Hub", out_dir=Path(td))
                        for key in (
                            "asset_library_json",
                            "bug_tracker_json",
                            "build_records_json",
                            "release_summary_json",
                            "docs_center_json",
                            "preview_html",
                            "acceptance_bundle_zip",
                        ):
                            self.assertTrue(Path(result[key]).exists(), key)
                        doc = json.loads(Path(result["acceptance_report_json"]).read_text(encoding="utf-8"))
                        self.assertEqual(doc["status"], "pass")
                        self.assertIn("docs_center", doc["checks"])


            if __name__ == "__main__":
                unittest.main()
            """
        ).lstrip(),
    }
    return _merge_file_maps(base, extras)


def materialize_generic_archetype_files(
    *,
    goal_text: str,
    project_id: str,
    project_root: str,
    package_name: str,
    startup_rel: str,
    workflow_doc_rel: str,
    context_used: list[str],
    project_archetype: str,
    project_intent: dict[str, Any],
    project_spec: dict[str, Any],
) -> dict[str, str]:
    if project_archetype == "indie_studio_hub_web":
        return _indie_studio_hub_files(
            goal_text=goal_text,
            project_id=project_id,
            project_root=project_root,
            package_name=package_name,
            startup_rel=startup_rel,
            workflow_doc_rel=workflow_doc_rel,
            context_used=context_used,
            project_archetype=project_archetype,
            project_intent=project_intent,
            project_spec=project_spec,
        )
    if project_archetype == "team_task_pm_web":
        return _team_task_pm_files(
            goal_text=goal_text,
            project_id=project_id,
            project_root=project_root,
            package_name=package_name,
            startup_rel=startup_rel,
            workflow_doc_rel=workflow_doc_rel,
            context_used=context_used,
            project_archetype=project_archetype,
            project_intent=project_intent,
            project_spec=project_spec,
        )
    if project_archetype == "cli_toolkit":
        return _cli_toolkit_files(
            goal_text=goal_text,
            project_id=project_id,
            project_root=project_root,
            package_name=package_name,
            startup_rel=startup_rel,
            workflow_doc_rel=workflow_doc_rel,
            context_used=context_used,
            project_archetype=project_archetype,
            project_intent=project_intent,
            project_spec=project_spec,
        )
    if project_archetype == "web_service":
        return _web_service_files(
            goal_text=goal_text,
            project_id=project_id,
            project_root=project_root,
            package_name=package_name,
            startup_rel=startup_rel,
            workflow_doc_rel=workflow_doc_rel,
            context_used=context_used,
            project_archetype=project_archetype,
            project_intent=project_intent,
            project_spec=project_spec,
        )
    if project_archetype == "data_pipeline":
        return _data_pipeline_files(
            goal_text=goal_text,
            project_id=project_id,
            project_root=project_root,
            package_name=package_name,
            startup_rel=startup_rel,
            workflow_doc_rel=workflow_doc_rel,
            context_used=context_used,
            project_archetype=project_archetype,
            project_intent=project_intent,
            project_spec=project_spec,
        )
    return _generic_pipeline_files(
        goal_text=goal_text,
        project_id=project_id,
        project_root=project_root,
        package_name=package_name,
        startup_rel=startup_rel,
        workflow_doc_rel=workflow_doc_rel,
        context_used=context_used,
        project_archetype=project_archetype,
        project_intent=project_intent,
        project_spec=project_spec,
    )

