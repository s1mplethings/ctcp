#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools import v2p_fixtures


def _write_fixture(path: Path, *, with_sem: bool = False, with_ref: bool = False) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "depth.npy").write_bytes(b"fixture-depth")
    (path / "poses.npy").write_bytes(b"fixture-poses")
    (path / "intrinsics.json").write_text(
        json.dumps({"fx": 10.0, "fy": 10.0, "cx": 1.0, "cy": 1.0}),
        encoding="utf-8",
    )
    if with_sem:
        (path / "sem.npy").write_bytes(b"fixture-sem")
    if with_ref:
        (path / "ref_cloud.ply").write_text("ply\nformat ascii 1.0\nelement vertex 0\nend_header\n", encoding="utf-8")


def _write_make_synth_fixture_script(repo: Path) -> None:
    script = repo / "scripts" / "make_synth_fixture.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(
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


class V2PFixtureDiscoveryTests(unittest.TestCase):
    def test_discover_fixtures_respects_required_files_and_depth(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "fixtures_root"
            _write_fixture(root / "a" / "good", with_sem=True)
            _write_fixture(root / "d1" / "d2" / "d3" / "d4" / "d5" / "too_deep")
            (root / "b" / "not_fixture").mkdir(parents=True, exist_ok=True)

            found = v2p_fixtures.discover_fixtures([root], max_depth=4)
            paths = {str(row.path) for row in found}
            self.assertIn(str((root / "a" / "good").resolve()), paths)
            self.assertNotIn(str((root / "d1" / "d2" / "d3" / "d4" / "d5" / "too_deep").resolve()), paths)

    def test_ensure_fixture_auto_uses_discovered_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            env_root = base / "env_fixtures"
            _write_fixture(env_root / "pick_me", with_ref=True)
            repo = base / "repo"
            repo.mkdir(parents=True, exist_ok=True)
            run_dir = base / "runs" / "cos_user_v2p" / "r1"
            run_dir.mkdir(parents=True, exist_ok=True)

            called = {"value": False}

            def _dialogue(_qid: str, _question: str, _default: str) -> str:
                called["value"] = True
                return _default

            backup = os.environ.get("V2P_FIXTURES_ROOT")
            os.environ["V2P_FIXTURES_ROOT"] = str(env_root)
            try:
                result = v2p_fixtures.ensure_fixture(
                    mode="auto",
                    repo=repo,
                    run_dir=run_dir,
                    user_dialogue=_dialogue,
                    runs_root=base / "runs",
                )
            finally:
                if backup is None:
                    os.environ.pop("V2P_FIXTURES_ROOT", None)
                else:
                    os.environ["V2P_FIXTURES_ROOT"] = backup

            self.assertFalse(called["value"])
            self.assertTrue(str(result.source).startswith("auto_discovered:"))
            self.assertTrue((result.path / "depth.npy").exists())
            self.assertTrue(result.has_ref_cloud)

    def test_ensure_fixture_synth_generates_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            repo = base / "repo"
            repo.mkdir(parents=True, exist_ok=True)
            _write_make_synth_fixture_script(repo)
            run_dir = base / "runs" / "cos_user_v2p" / "r2"
            run_dir.mkdir(parents=True, exist_ok=True)

            def _dialogue(qid: str, _question: str, _default: str) -> str:
                return _default

            result = v2p_fixtures.ensure_fixture(
                mode="synth",
                repo=repo,
                run_dir=run_dir,
                user_dialogue=_dialogue,
                runs_root=base / "runs",
            )
            self.assertEqual(result.source, "synth")
            self.assertTrue((result.path / "depth.npy").exists())
            self.assertTrue((result.path / "poses.npy").exists())
            self.assertTrue((result.path / "intrinsics.json").exists())


if __name__ == "__main__":
    unittest.main()
