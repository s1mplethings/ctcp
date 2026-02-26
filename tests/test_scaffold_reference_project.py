#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
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


def _parse_run_dir(stdout: str) -> Path:
    for line in (stdout or "").splitlines():
        if "run_dir=" in line:
            raw = line.split("run_dir=", 1)[1].strip()
            return Path(raw)
    raise AssertionError(f"run_dir not found in output:\n{stdout}")


class ScaffoldReferenceProjectTests(unittest.TestCase):
    def test_scaffold_minimal_generates_expected_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            out_dir = base / "my_new_proj"
            runs_root = base / "runs_root"
            cmd = [
                "python",
                "scripts/ctcp_orchestrate.py",
                "scaffold",
                "--profile",
                "minimal",
                "--out",
                str(out_dir),
                "--name",
                "my_new_proj",
                "--runs-root",
                str(runs_root),
            ]
            proc = _run(cmd, ROOT)
            self.assertEqual(proc.returncode, 0, msg=f"{proc.stdout}\n{proc.stderr}")

            required = [
                out_dir / "README.md",
                out_dir / "docs" / "00_CORE.md",
                out_dir / "meta" / "tasks" / "CURRENT.md",
                out_dir / "meta" / "reports" / "LAST.md",
                out_dir / "scripts" / "verify_repo.ps1",
                out_dir / "scripts" / "verify_repo.sh",
                out_dir / "manifest.json",
                out_dir / "TREE.md",
            ]
            for path in required:
                self.assertTrue(path.exists(), msg=f"missing expected file: {path}")

            manifest_doc = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
            manifest_files = manifest_doc.get("files", [])
            self.assertIsInstance(manifest_files, list)
            self.assertGreater(len(manifest_files), 0)
            for rel in manifest_files:
                self.assertTrue((out_dir / Path(str(rel))).exists(), msg=f"manifest missing path: {rel}")

            run_dir = _parse_run_dir(proc.stdout)
            self.assertTrue(run_dir.exists(), msg=f"missing run_dir: {run_dir}")
            self.assertTrue((run_dir / "TRACE.md").exists())
            self.assertTrue((run_dir / "artifacts" / "scaffold_report.json").exists())

            report_doc = json.loads((run_dir / "artifacts" / "scaffold_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report_doc.get("result"), "PASS")
            self.assertEqual(report_doc.get("out_dir"), str(out_dir.resolve()))


if __name__ == "__main__":
    unittest.main()
