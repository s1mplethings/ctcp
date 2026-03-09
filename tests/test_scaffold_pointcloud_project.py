#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=proc_env,
    )


def _parse_run_dir(stdout: str) -> Path:
    for line in (stdout or "").splitlines():
        if "run_dir=" in line:
            return Path(line.split("run_dir=", 1)[1].strip())
    raise AssertionError(f"run_dir not found in output:\n{stdout}")


def _restore_last_run_pointer(pointer_path: Path, pointer_exists: bool, pointer_before: str) -> None:
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    if pointer_exists:
        pointer_path.write_text(pointer_before, encoding="utf-8")
    else:
        if pointer_path.exists():
            pointer_path.unlink()


def _assert_expected_pointcloud_files(out_dir: Path) -> None:
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
        if not path.exists():
            raise AssertionError(f"missing expected file: {path}")


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

                _assert_expected_pointcloud_files(out_dir)

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

                run_dir = _parse_run_dir(proc.stdout)
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
                _restore_last_run_pointer(pointer_path, pointer_exists, pointer_before)

    def test_scaffold_pointcloud_live_reference_generates_metadata_and_whitelist_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            pointer_path = ROOT / "meta" / "run_pointers" / "LAST_RUN.txt"
            pointer_exists = pointer_path.exists()
            pointer_before = pointer_path.read_text(encoding="utf-8") if pointer_exists else ""
            out_dir = base / "v2p_live_ref"
            runs_root = base / "ctcp_runs"
            cmd = [
                sys.executable,
                "scripts/ctcp_orchestrate.py",
                "scaffold-pointcloud",
                "--out",
                str(out_dir),
                "--name",
                "v2p_live_ref",
                "--profile",
                "minimal",
                "--source-mode",
                "live-reference",
                "--runs-root",
                str(runs_root),
                "--dialogue-script",
                str(ROOT / "tests" / "fixtures" / "dialogues" / "scaffold_pointcloud.jsonl"),
            ]
            try:
                proc = _run(cmd, ROOT)
                self.assertEqual(proc.returncode, 0, msg=f"{proc.stdout}\n{proc.stderr}")
                _assert_expected_pointcloud_files(out_dir)
                self.assertTrue((out_dir / "meta" / "reference_source.json").exists())
                self.assertTrue((out_dir / "meta" / "reference_tokens.md").exists())

                manifest_doc = json.loads((out_dir / "meta" / "manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest_doc.get("source_mode"), "live-reference")
                self.assertTrue(str(manifest_doc.get("source_commit", "")).strip())
                self.assertIsInstance(manifest_doc.get("inherited_copy"), list)
                self.assertIsInstance(manifest_doc.get("inherited_transform"), list)
                self.assertIsInstance(manifest_doc.get("generated"), list)
                effective_project_name = str(manifest_doc.get("project_name", ""))

                ref_doc = json.loads((out_dir / "meta" / "reference_source.json").read_text(encoding="utf-8"))
                self.assertEqual(ref_doc.get("source_mode"), "live-reference")
                self.assertTrue(str(ref_doc.get("source_commit", "")).strip())
                self.assertEqual(ref_doc.get("profile"), "minimal")
                self.assertEqual(str(ref_doc.get("export_manifest", "")), "meta/reference_export_manifest.yaml")
                self.assertIn("meta/reference_source.json", list(ref_doc.get("generated_files", [])))

                token_text = (out_dir / "meta" / "reference_tokens.md").read_text(encoding="utf-8")
                expected_slug = effective_project_name.lower().replace(" ", "-")
                self.assertIn(f"project_name={effective_project_name}", token_text)
                self.assertIn(f"project_slug={expected_slug}", token_text)
                self.assertIn("source_mode=live-reference", token_text)
                self.assertNotIn("{{", token_text)
                self.assertNotIn("}}", token_text)

                for node in out_dir.rglob("*"):
                    rel = node.relative_to(out_dir).as_posix()
                    self.assertNotIn("__pycache__", rel)
                    self.assertNotIn(".pytest_cache", rel)
                    self.assertNotIn("/runs/", f"/{rel}/")
                    self.assertNotIn("/out/", f"/{rel}/")
                    self.assertNotIn("/fixture/", f"/{rel}/")
                    self.assertFalse(rel.startswith(".git/"))

                # live-reference must not mirror full CTCP repository tree.
                self.assertFalse((out_dir / "src").exists())
                self.assertFalse((out_dir / "frontend").exists())
                self.assertFalse((out_dir / ".agents").exists())
                self.assertFalse((out_dir / "templates").exists())

                run_dir = _parse_run_dir(proc.stdout)
                report = json.loads((run_dir / "artifacts" / "scaffold_pointcloud_report.json").read_text(encoding="utf-8"))
                self.assertEqual(report.get("result"), "PASS")
                self.assertEqual(report.get("source_mode"), "live-reference")
                self.assertTrue(str(report.get("source_commit", "")).strip())
                self.assertTrue(str(report.get("export_manifest_path", "")).strip())
                counts = report.get("counts", {}) or {}
                self.assertGreater(int(counts.get("inherited_copy_count", 0)), 0)
                self.assertGreater(int(counts.get("inherited_transform_count", 0)), 0)
            finally:
                _restore_last_run_pointer(pointer_path, pointer_exists, pointer_before)

    def test_scaffold_pointcloud_live_reference_source_commit_fallback_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            pointer_path = ROOT / "meta" / "run_pointers" / "LAST_RUN.txt"
            pointer_exists = pointer_path.exists()
            pointer_before = pointer_path.read_text(encoding="utf-8") if pointer_exists else ""
            out_dir = base / "v2p_unknown_commit"
            runs_root = base / "ctcp_runs"
            cmd = [
                sys.executable,
                "scripts/ctcp_orchestrate.py",
                "scaffold-pointcloud",
                "--out",
                str(out_dir),
                "--name",
                "v2p_unknown_commit",
                "--profile",
                "minimal",
                "--source-mode",
                "live-reference",
                "--runs-root",
                str(runs_root),
                "--dialogue-script",
                str(ROOT / "tests" / "fixtures" / "dialogues" / "scaffold_pointcloud.jsonl"),
            ]
            try:
                proc = _run(cmd, ROOT, env={"CTCP_DISABLE_GIT_SOURCE": "1"})
                self.assertEqual(proc.returncode, 0, msg=f"{proc.stdout}\n{proc.stderr}")
                ref_doc = json.loads((out_dir / "meta" / "reference_source.json").read_text(encoding="utf-8"))
                self.assertEqual(ref_doc.get("source_commit"), "unknown")
                manifest_doc = json.loads((out_dir / "meta" / "manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest_doc.get("source_commit"), "unknown")
            finally:
                _restore_last_run_pointer(pointer_path, pointer_exists, pointer_before)

    def test_scaffold_pointcloud_force_refuses_unmanaged_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            out_dir = base / "v2p_force_guard"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "unknown.txt").write_text("keep me", encoding="utf-8")
            cmd = [
                sys.executable,
                "scripts/ctcp_orchestrate.py",
                "scaffold-pointcloud",
                "--out",
                str(out_dir),
                "--name",
                "v2p_force_guard",
                "--profile",
                "minimal",
                "--force",
                "--runs-root",
                str(base / "ctcp_runs"),
                "--dialogue-script",
                str(ROOT / "tests" / "fixtures" / "dialogues" / "scaffold_pointcloud.jsonl"),
            ]
            proc = _run(cmd, ROOT)
            self.assertNotEqual(proc.returncode, 0, msg=f"{proc.stdout}\n{proc.stderr}")
            self.assertIn("requires an existing generated manifest", f"{proc.stdout}\n{proc.stderr}")

    def test_scaffold_pointcloud_rejects_out_inside_repo_root(self) -> None:
        out_dir = ROOT / "tests" / "_tmp_inside_repo_out"
        if out_dir.exists():
            for node in sorted(out_dir.rglob("*"), reverse=True):
                if node.is_file() or node.is_symlink():
                    node.unlink()
                elif node.is_dir():
                    try:
                        node.rmdir()
                    except OSError:
                        pass
            try:
                out_dir.rmdir()
            except OSError:
                pass
        cmd = [
            sys.executable,
            "scripts/ctcp_orchestrate.py",
            "scaffold-pointcloud",
            "--out",
            str(out_dir),
            "--name",
            "tmp_inside_repo_out",
            "--profile",
            "minimal",
            "--runs-root",
            str(ROOT / "tests" / "_tmp_runs"),
            "--dialogue-script",
            str(ROOT / "tests" / "fixtures" / "dialogues" / "scaffold_pointcloud.jsonl"),
        ]
        proc = _run(cmd, ROOT)
        self.assertNotEqual(proc.returncode, 0, msg=f"{proc.stdout}\n{proc.stderr}")
        self.assertIn("must be outside repo root", f"{proc.stdout}\n{proc.stderr}")

    def test_scaffold_pointcloud_live_reference_rejects_path_traversal_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            out_dir = base / "v2p_traversal_guard"
            cmd = [
                sys.executable,
                "scripts/ctcp_orchestrate.py",
                "scaffold-pointcloud",
                "--out",
                str(out_dir),
                "--name",
                "v2p_traversal_guard",
                "--profile",
                "minimal",
                "--source-mode",
                "live-reference",
                "--reference-manifest",
                "tests/fixtures/reference_export/bad_traversal_source_manifest.yaml",
                "--runs-root",
                str(base / "ctcp_runs"),
                "--dialogue-script",
                str(ROOT / "tests" / "fixtures" / "dialogues" / "scaffold_pointcloud.jsonl"),
            ]
            proc = _run(cmd, ROOT)
            self.assertNotEqual(proc.returncode, 0, msg=f"{proc.stdout}\n{proc.stderr}")
            self.assertIn("path traversal is not allowed", f"{proc.stdout}\n{proc.stderr}")


if __name__ == "__main__":
    unittest.main()
