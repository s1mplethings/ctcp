#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import stat
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


def _parse_run_dir(stdout: str) -> Path:
    for line in (stdout or "").splitlines():
        if "run_dir=" in line:
            raw = line.split("run_dir=", 1)[1].strip()
            return Path(raw)
    raise AssertionError(f"run_dir not found in output:\n{stdout}")


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


class CosUserV2PRunnerTests(unittest.TestCase):
    def test_cos_user_v2p_stub_generates_outputs_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            pointer_path = ROOT / "meta" / "run_pointers" / "LAST_RUN.txt"
            pointer_exists = pointer_path.exists()
            pointer_before = pointer_path.read_text(encoding="utf-8") if pointer_exists else ""
            target_repo = base / "target_repo"
            target_repo.mkdir(parents=True, exist_ok=True)
            scripts_dir = target_repo / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            (target_repo / "verify_repo.ps1").write_text('Write-Output "wrong verify location"\nexit 99\n', encoding="utf-8")
            (target_repo / "verify_repo.sh").write_text('#!/usr/bin/env bash\necho "wrong verify location"\nexit 99\n', encoding="utf-8")
            (scripts_dir / "verify_repo.ps1").write_text('Write-Output "verify ok"\nexit 0\n', encoding="utf-8")
            verify_sh = scripts_dir / "verify_repo.sh"
            verify_sh.write_text('#!/usr/bin/env bash\necho "verify ok"\nexit 0\n', encoding="utf-8")
            (scripts_dir / "make_synth_fixture.py").write_text(
                "\n".join(
                    [
                        "from __future__ import annotations",
                        "import argparse, json, pathlib",
                        "ap = argparse.ArgumentParser()",
                        "ap.add_argument('--out', default='fixture')",
                        "args = ap.parse_args()",
                        "out = pathlib.Path(args.out)",
                        "out.mkdir(parents=True, exist_ok=True)",
                        "(out / 'depth.npy').write_bytes(b'fixture-depth')",
                        "(out / 'poses.npy').write_bytes(b'fixture-poses')",
                        "(out / 'intrinsics.json').write_text(json.dumps({'fx':10.0,'fy':10.0,'cx':1.0,'cy':1.0}), encoding='utf-8')",
                        "(out / 'sem.npy').write_bytes(b'fixture-sem')",
                        "(out / 'ref_cloud.ply').write_text('ply\\nformat ascii 1.0\\nelement vertex 0\\nend_header\\n', encoding='utf-8')",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            try:
                verify_sh.chmod(verify_sh.stat().st_mode | stat.S_IXUSR)
            except OSError:
                pass

            out_root = base / "v2p_tests"
            runs_root = base / "ctcp_runs"
            cmd = [
                sys.executable,
                "scripts/ctcp_orchestrate.py",
                "cos-user-v2p",
                "--repo",
                str(target_repo),
                "--project",
                "v2p_lab",
                "--out-root",
                str(out_root),
                "--testkit-zip",
                str(ROOT / "tests" / "fixtures" / "testkits" / "stub_ok.zip"),
                "--entry",
                "python run_all.py",
                "--fixture-mode",
                "synth",
                "--dialogue-script",
                str(ROOT / "tests" / "fixtures" / "dialogues" / "v2p_cos_user.jsonl"),
                "--runs-root",
                str(runs_root),
                "--force",
            ]
            try:
                proc = _run(cmd, ROOT)
                self.assertEqual(proc.returncode, 0, msg=f"{proc.stdout}\n{proc.stderr}")

                run_dir = _parse_run_dir(proc.stdout)
                self.assertTrue(run_dir.exists(), msg=f"missing run_dir: {run_dir}")
                self.assertTrue((run_dir / "TRACE.md").exists())
                self.assertTrue((run_dir / "events.jsonl").exists())
                self.assertTrue((run_dir / "artifacts" / "USER_SIM_PLAN.md").exists())
                self.assertTrue((run_dir / "artifacts" / "dialogue.jsonl").exists())
                self.assertTrue((run_dir / "artifacts" / "dialogue_transcript.md").exists())
                self.assertTrue((run_dir / "artifacts" / "fixture_meta.json").exists())
                self.assertTrue((run_dir / "artifacts" / "v2p_report.json").exists())

                report = json.loads((run_dir / "artifacts" / "v2p_report.json").read_text(encoding="utf-8"))
                self.assertEqual(report.get("result"), "PASS")
                self.assertGreaterEqual(int(report.get("dialogue_turns", 0)), 3)
                self.assertEqual((report.get("verify", {}) or {}).get("pre_rc"), 0)
                self.assertEqual((report.get("verify", {}) or {}).get("post_rc"), 0)
                pre_cmd = str((report.get("verify", {}) or {}).get("pre_cmd", ""))
                self.assertIn("scripts", pre_cmd)
                self.assertIn("verify_repo", pre_cmd)
                fixture_meta = json.loads((run_dir / "artifacts" / "fixture_meta.json").read_text(encoding="utf-8"))
                self.assertEqual(fixture_meta.get("source"), "synth")
                self.assertTrue(Path(str(fixture_meta.get("path", ""))).exists())

                sandbox_dir = Path(str((report.get("paths", {}) or {}).get("sandbox_dir", "")))
                self.assertTrue(sandbox_dir.exists(), msg=f"sandbox dir missing: {sandbox_dir}")
                self.assertFalse(_is_within(sandbox_dir, ROOT), msg=f"sandbox must be outside CTCP repo: {sandbox_dir}")
                self.assertFalse(
                    _is_within(sandbox_dir, target_repo),
                    msg=f"sandbox must be outside target repo: {sandbox_dir}",
                )

                run_id = str(report.get("run_id"))
                out_dir = out_root / "v2p_lab" / run_id / "out"
                self.assertTrue((out_dir / "scorecard.json").exists())
                self.assertTrue((out_dir / "eval.json").exists())
                self.assertTrue((out_dir / "cloud.ply").exists())
                self.assertTrue((out_dir / "cloud_sem.ply").exists())

                self.assertTrue((run_dir / "logs" / "verify_pre.log").exists())
                self.assertTrue((run_dir / "logs" / "verify_post.log").exists())
                self.assertTrue((run_dir / "logs" / "testkit_stdout.log").exists())
                self.assertTrue((run_dir / "logs" / "testkit_stderr.log").exists())
            finally:
                pointer_path.parent.mkdir(parents=True, exist_ok=True)
                if pointer_exists:
                    pointer_path.write_text(pointer_before, encoding="utf-8")
                else:
                    if pointer_path.exists():
                        pointer_path.unlink()


if __name__ == "__main__":
    unittest.main()
