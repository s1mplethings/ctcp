from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path


FILES = [
    Path("README.md"),
    Path("meta/tasks/CURRENT.md"),
    Path("meta/reports/LAST.md"),
]


def _newline_for(path: Path) -> str:
    return "\r\n" if b"\r\n" in path.read_bytes() else "\n"


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    updated = text.replace(old, new, 1)
    if updated == text:
        raise SystemExit(f"[generate_s16_fix_patch] missing anchor for {label}")
    return updated


def build_patch(repo_root: Path, run_dir: Path) -> Path:
    temp_root = repo_root / ".agent_private"
    temp_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="s16_patch_", dir=temp_root) as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        for rel in FILES:
            dest = tmp_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((repo_root / rel).read_bytes())

        subprocess.run(["git", "init"], cwd=tmp_dir, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.email", "codex@example.com"], cwd=tmp_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Codex"], cwd=tmp_dir, check=True)
        subprocess.run(["git", "add", "."], cwd=tmp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_dir, check=True, stdout=subprocess.DEVNULL)

        readme = tmp_dir / "README.md"
        readme_text = readme.read_text(encoding="utf-8")
        decision_log_line = "- [ai_context/decision_log.md](ai_context/decision_log.md)\n"
        if decision_log_line not in readme_text:
            readme.write_text(
                _replace_once(
                    readme_text,
                    "- [ai_context/problem_registry.md](ai_context/problem_registry.md)\n",
                    "- [ai_context/problem_registry.md](ai_context/problem_registry.md)\n"
                    "- [ai_context/decision_log.md](ai_context/decision_log.md)\n",
                    "README.md",
                ),
                encoding="utf-8",
                newline=_newline_for(repo_root / "README.md"),
            )

        current_task = tmp_dir / "meta/tasks/CURRENT.md"
        current_task_text = current_task.read_text(encoding="utf-8")
        current_task.write_text(
            _replace_once(
                current_task_text,
                "## Queue Binding\n\n",
                "## Queue Binding\n\n<!-- simlab-s16-touch-current -->\n\n",
                "meta/tasks/CURRENT.md",
            ),
            encoding="utf-8",
            newline=_newline_for(repo_root / "meta/tasks/CURRENT.md"),
        )

        last_report = tmp_dir / "meta/reports/LAST.md"
        last_report_text = last_report.read_text(encoding="utf-8")
        last_report.write_text(
            _replace_once(
                last_report_text,
                "### Changes\n\n",
                "### Changes\n\n<!-- simlab-s16-touch-report -->\n\n",
                "meta/reports/LAST.md",
            ),
            encoding="utf-8",
            newline=_newline_for(repo_root / "meta/reports/LAST.md"),
        )

        diff = subprocess.run(
            ["git", "diff", "--", "README.md", "meta/tasks/CURRENT.md", "meta/reports/LAST.md"],
            cwd=tmp_dir,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        ).stdout.replace("\r\n", "\n")

    if not diff.startswith("diff --git "):
        raise SystemExit("[generate_s16_fix_patch] missing diff header")

    out_path = run_dir / "artifacts" / "diff.patch"
    out_path.write_text(diff, encoding="utf-8", newline="\n")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the stable S16 fixer-loop patch.")
    parser.add_argument("--run-dir-file", required=True)
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    run_dir = Path(Path(args.run_dir_file).read_text(encoding="utf-8").strip())
    out_path = build_patch(repo_root, run_dir)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
