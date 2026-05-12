from __future__ import annotations

import json
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.providers.project_generation_contracts import converge_contract_graph


def _load_benchmark_module():
    path = ROOT / "tests" / "concrete_project_benchmark" / "run_concrete_project_benchmark.py"
    spec = importlib.util.spec_from_file_location("ctcp_concrete_benchmark_for_tests", path)
    if spec is None or spec.loader is None:
        raise ImportError(str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


benchmark = _load_benchmark_module()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ConvergencePerformanceGuardTests(unittest.TestCase):
    def test_convergence_max_passes_enforced(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_max_passes_") as td:
            run_dir = Path(td)
            project = run_dir / "project_output" / "app"
            _write(project / "src" / "app" / "service.py", "class IssueService:\n    def get_issues(self):\n        return []\n")
            _write(project / "src" / "app" / "app.py", "from app.service import IssueService\nservice = IssueService()\nservice.list_issues()\n")

            report = converge_contract_graph(run_dir, project_root="project_output/app", repair=True, max_passes=1)

            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["stopped_reason"], "max_passes")
            self.assertEqual(report["max_passes"], 1)
            self.assertTrue(report["pass_timings"])

    def test_convergence_max_wall_clock_enforced_gracefully(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_max_wall_") as td:
            run_dir = Path(td)
            project = run_dir / "project_output" / "app"
            _write(project / "src" / "app" / "service.py", "class IssueService:\n    def get_issues(self):\n        return []\n")

            counter = {"value": 0.0}

            def fake_monotonic() -> float:
                counter["value"] += 999.0
                return counter["value"]

            with mock.patch("tools.providers.project_generation_contracts.time.monotonic", side_effect=fake_monotonic):
                report = converge_contract_graph(run_dir, project_root="project_output/app", repair=True, max_wall_clock_seconds=1)

            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["stopped_reason"], "max_wall_clock")

    def test_graph_extraction_cache_hit_miss_and_changed_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_cache_") as td:
            run_dir = Path(td)
            project = run_dir / "project_output" / "app"
            service = project / "src" / "app" / "service.py"
            app = project / "src" / "app" / "app.py"
            _write(service, "class IssueService:\n    def get_issues(self):\n        return []\n")
            _write(app, "def main():\n    return 'ok'\n")

            first = converge_contract_graph(run_dir, project_root="project_output/app")
            second = converge_contract_graph(run_dir, project_root="project_output/app")
            _write(app, "def main():\n    return 'changed'\n")
            third = converge_contract_graph(run_dir, project_root="project_output/app")

            self.assertGreaterEqual(first["cache"]["cache_misses"], 2)
            self.assertGreaterEqual(second["cache"]["cache_hits"], 2)
            self.assertEqual(second["cache"]["changed_files"], [])
            self.assertIn("src/app/app.py", third["cache"]["changed_files"])
            self.assertNotIn("src/app/service.py", third["cache"]["changed_files"])

    def test_cache_corruption_fallback_and_provider_count(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_cache_corrupt_") as td:
            run_dir = Path(td)
            project = run_dir / "project_output" / "app"
            _write(project / "src" / "app" / "service.py", "class IssueService:\n    pass\n")
            _write(run_dir / "artifacts" / "file_hash_cache.json", "{not json")

            report = converge_contract_graph(run_dir, project_root="project_output/app")

            self.assertTrue(report["cache"]["corrupted"])
            self.assertTrue(report["cache"]["fallback_full_scan"])
            self.assertEqual(report["provider_call_count"], 0)
            self.assertIn("stopped_reason", report)
            self.assertTrue(report["pass_timings"])

    def test_benchmark_summary_includes_step_timings(self) -> None:
        summary: dict[str, object] = {"step_timings": [], "timeout_step": ""}
        benchmark._record_step(summary, "source_generation", benchmark.time.time(), status="passed")
        self.assertEqual(summary["step_timings"][0]["step"], "source_generation")
        self.assertIn("duration_seconds", summary["step_timings"][0])

    def test_runtime_probe_timeout_returns_failed_without_hanging(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_probe_") as td:
            root = Path(td)
            project = root / "project"
            script = project / "scripts" / "run_project_web.py"
            _write(script, "import time\ntime.sleep(30)\n")
            old_startup = benchmark.SERVER_STARTUP_TIMEOUT_SECONDS
            old_shutdown = benchmark.SERVER_SHUTDOWN_TIMEOUT_SECONDS
            benchmark.SERVER_STARTUP_TIMEOUT_SECONDS = 1
            benchmark.SERVER_SHUTDOWN_TIMEOUT_SECONDS = 1
            try:
                routes = [
                    {"method": method, "path": path, "handler": "scripts/run_project_web.py:main"}
                    for method, path in (item.split(" ", 1) for item in benchmark._required_fixture_route_keys())
                ]
                result = benchmark._probe_http_api(
                    project,
                    "",
                    {"step_timings": [], "timeout_step": ""},
                    {
                        "routes": {"routes": routes},
                        "runtime": {
                            "entrypoint": "scripts/run_project_web.py",
                            "supported_cli_args": [],
                            "default_host": "127.0.0.1",
                            "default_port": benchmark._free_port(),
                        },
                    },
                )
            finally:
                benchmark.SERVER_STARTUP_TIMEOUT_SECONDS = old_startup
                benchmark.SERVER_SHUTDOWN_TIMEOUT_SECONDS = old_shutdown

            self.assertFalse(result["passed"])
            self.assertEqual(result["reason"], "no candidate stayed up with a registered route endpoint")


if __name__ == "__main__":
    unittest.main()
