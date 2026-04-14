from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from scripts.delivery_replay_validator import run_delivery_replay_check


def _zip_tree(root: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(root))


class DeliveryReplayValidatorTests(unittest.TestCase):
    def test_missing_package_fails_with_explicit_stage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_replay_missing_pkg_") as td:
            report = run_delivery_replay_check(
                package_path=Path(td) / "missing.zip",
                output_root=Path(td) / "replay",
            )

        self.assertFalse(bool(report.get("overall_pass", False)))
        self.assertEqual(str(report.get("first_failure_stage", "")), "package_missing")

    def test_extractable_package_without_entrypoint_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_replay_no_entry_") as td:
            root = Path(td)
            package_src = root / "pkg"
            package_src.mkdir(parents=True, exist_ok=True)
            (package_src / "README.md").write_text("# package only\n", encoding="utf-8")
            package_path = root / "package.zip"
            _zip_tree(package_src, package_path)

            report = run_delivery_replay_check(package_path=package_path, output_root=root / "replay")

        self.assertFalse(bool(report.get("overall_pass", False)))
        self.assertEqual(str(report.get("first_failure_stage", "")), "entrypoint_missing")

    def test_cli_package_replay_passes_and_writes_report_and_screenshot(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_replay_cli_ok_") as td:
            root = Path(td)
            project = root / "project"
            scripts_dir = project / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            (project / "README.md").write_text("# replay demo\n", encoding="utf-8")
            (scripts_dir / "run_project_cli.py").write_text(
                "\n".join(
                    [
                        "from __future__ import annotations",
                        "import argparse",
                        "import json",
                        "from pathlib import Path",
                        "",
                        "def main() -> int:",
                        "    ap = argparse.ArgumentParser()",
                        "    ap.add_argument('--goal', default='')",
                        "    ap.add_argument('--project-name', default='')",
                        "    ap.add_argument('--out', default='')",
                        "    args = ap.parse_args()",
                        "    if not args.out:",
                        "        return 0",
                        "    out_dir = Path(args.out)",
                        "    out_dir.mkdir(parents=True, exist_ok=True)",
                        "    spec = out_dir / 'mvp_spec.json'",
                        "    summary = out_dir / 'delivery_summary.md'",
                        "    spec.write_text(json.dumps({'goal': args.goal, 'project_name': args.project_name}, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')",
                        "    summary.write_text('# replay summary\\n', encoding='utf-8')",
                        "    print(json.dumps({'mvp_spec_json': str(spec), 'delivery_summary_md': str(summary)}, ensure_ascii=False))",
                        "    return 0",
                        "",
                        "if __name__ == '__main__':",
                        "    raise SystemExit(main())",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            package_path = root / "package.zip"
            _zip_tree(project, package_path)

            report = run_delivery_replay_check(package_path=package_path, output_root=root / "replay")
            report_path = root / "replay" / "replay_artifacts" / "replay_report.json"
            saved = json.loads(report_path.read_text(encoding="utf-8"))
            screenshot_path = Path(str(report.get("replay_screenshot_path", "")))
            self.assertTrue(screenshot_path.exists(), msg=str(screenshot_path))
            self.assertGreater(screenshot_path.stat().st_size, 0)

        self.assertTrue(bool(report.get("overall_pass", False)), msg=json.dumps(report, ensure_ascii=False))
        self.assertTrue(bool(saved.get("overall_pass", False)), msg=json.dumps(saved, ensure_ascii=False))
        self.assertEqual(str(report.get("entrypoint_detected", "")), "scripts/run_project_cli.py")


if __name__ == "__main__":
    unittest.main()
