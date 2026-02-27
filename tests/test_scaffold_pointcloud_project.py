#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class ScaffoldPointcloudProjectTests(unittest.TestCase):
    def test_pointcloud_template_tree_has_no_runtime_artifacts(self) -> None:
        template_root = ROOT / "templates" / "pointcloud_project"
        forbidden_dir_names = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
        forbidden_file_names = {"Thumbs.db", ".DS_Store"}
        for node in template_root.rglob("*"):
            if node.name in forbidden_dir_names:
                self.fail(f"forbidden template runtime directory found: {node}")
            if node.name in forbidden_file_names:
                self.fail(f"forbidden template runtime file found: {node}")
            if node.is_file() and node.suffix == ".pyc":
                self.fail(f"forbidden template runtime file found: {node}")

    def test_scaffold_pointcloud_minimal_generates_expected_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            pointer_path = ROOT / "meta" / "run_pointers" / "LAST_RUN.txt"
            pointer_exists = pointer_path.exists()
            pointer_before = pointer_path.read_text(encoding="utf-8") if pointer_exists else ""
            out_dir = base / "v2p_project"
            runs_root = base / "ctcp_runs"
            cmd = [
                sys.executable,
                "scripts/ctcp_orchestrate.py",
                "scaffold-pointcloud",
                "--out",
                str(out_dir),
                "--name",
                "v2p_project",
                "--profile",
                "minimal",
                "--runs-root",
                str(runs_root),
                "--dialogue-script",
                str(ROOT / "tests" / "fixtures" / "dialogues" / "scaffold_pointcloud.jsonl"),
            ]
            try:
                proc = _run(cmd, ROOT)
                self.assertEqual(proc.returncode, 0, msg=f"{proc.stdout}\n{proc.stderr}")

                required = [
                    out_dir / "README.md",
                    out_dir / ".gitignore",
                    out_dir / "docs" / "00_CORE.md",
                    out_dir / "meta" / "tasks" / "CURRENT.md",
                    out_dir / "meta" / "reports" / "LAST.md",
                    out_dir / "meta" / "manifest.json",
                    out_dir / "scripts" / "make_synth_fixture.py",
                    out_dir / "scripts" / "eval_v2p.py",
                    out_dir / "scripts" / "clean_project.py",
                    out_dir / "scripts" / "run_v2p.py",
                    out_dir / "scripts" / "verify_repo.ps1",
                    out_dir / "tests" / "test_clean_project.py",
                    out_dir / "tests" / "test_pipeline_synth.py",
                    out_dir / "tests" / "test_smoke.py",
                    out_dir / "pyproject.toml",
                ]
                for path in required:
                    self.assertTrue(path.exists(), msg=f"missing expected file: {path}")

                manifest_doc = json.loads((out_dir / "meta" / "manifest.json").read_text(encoding="utf-8"))
                files = manifest_doc.get("files", [])
                self.assertIsInstance(files, list)
                self.assertGreater(len(files), 0)
                for rel in files:
                    self.assertTrue((out_dir / Path(str(rel))).exists(), msg=f"manifest missing path: {rel}")
                    normalized = str(rel).replace("\\", "/")
                    self.assertNotIn("__pycache__", normalized)
                    self.assertNotIn(".pytest_cache", normalized)
                    self.assertFalse(normalized.startswith("out/"))
                    self.assertFalse(normalized.startswith("fixture/"))
                    self.assertFalse(normalized.startswith("runs/"))

                run_dir = None
                for line in (proc.stdout or "").splitlines():
                    if "run_dir=" in line:
                        run_dir = Path(line.split("run_dir=", 1)[1].strip())
                        break
                self.assertIsNotNone(run_dir, msg=f"run_dir not found in output:\n{proc.stdout}")
                self.assertTrue(run_dir.exists(), msg=f"missing run_dir: {run_dir}")
                self.assertTrue((run_dir / "TRACE.md").exists())
                self.assertTrue((run_dir / "events.jsonl").exists())
                self.assertTrue((run_dir / "artifacts" / "SCAFFOLD_PLAN.md").exists())
                self.assertTrue((run_dir / "artifacts" / "dialogue.jsonl").exists())
                self.assertTrue((run_dir / "artifacts" / "dialogue_transcript.md").exists())
                self.assertTrue((run_dir / "artifacts" / "scaffold_pointcloud_report.json").exists())

                report = json.loads((run_dir / "artifacts" / "scaffold_pointcloud_report.json").read_text(encoding="utf-8"))
                self.assertEqual(report.get("result"), "PASS")
                self.assertEqual((report.get("dialogue", {}) or {}).get("turn_count"), 3)
            finally:
                pointer_path.parent.mkdir(parents=True, exist_ok=True)
                if pointer_exists:
                    pointer_path.write_text(pointer_before, encoding="utf-8")
                else:
                    if pointer_path.exists():
                        pointer_path.unlink()


if __name__ == "__main__":
    unittest.main()
