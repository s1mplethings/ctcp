from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _project_dir_from_startup(*, run_dir: Path, startup_entrypoint: str) -> Path:
    rel = str(startup_entrypoint or "").strip().replace("\\", "/")
    parts = [part for part in rel.split("/") if part]
    try:
        marker = parts.index("project_output")
    except ValueError:
        return (run_dir / rel).resolve().parent if rel else run_dir.resolve()
    if len(parts) >= marker + 2:
        return (run_dir / "/".join(parts[: marker + 2])).resolve()
    return run_dir.resolve()


def _import_style_violations(test_files: list[Path], *, project_dir: Path) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for path in test_files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
        except SyntaxError:
            continue
        rel = path.resolve().relative_to(project_dir.resolve()).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = str(node.module or "").strip()
                if module == "src" or module.startswith("src."):
                    violations.append(
                        {
                            "path": rel,
                            "import": f"from {module} import ...",
                            "reason": "generated tests must import the package name directly, not src.<package>",
                        }
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module = str(alias.name or "").strip()
                    if module == "src" or module.startswith("src."):
                        violations.append(
                            {
                                "path": rel,
                                "import": f"import {module}",
                                "reason": "generated tests must import the package name directly, not src.<package>",
                            }
                        )
    return violations


def generated_tests_validation(*, run_dir: Path, startup_entrypoint: str) -> dict[str, Any]:
    project_dir = _project_dir_from_startup(run_dir=run_dir, startup_entrypoint=startup_entrypoint)
    tests_dir = project_dir / "tests"
    test_files = sorted(path for path in tests_dir.rglob("test*.py") if path.is_file()) if tests_dir.exists() else []
    if not test_files:
        return {
            "passed": True,
            "status": "skipped",
            "reason": "no generated tests directory or test*.py files",
            "checked_files": [],
            "import_style_violations": [],
            "rc": 0,
            "stdout_tail": "",
            "stderr_tail": "",
        }
    import_style_violations = _import_style_violations(test_files, project_dir=project_dir)
    env = dict(os.environ)
    src_root = project_dir / "src"
    path_entries = [str(src_root)] if src_root.exists() else []
    existing = env.get("PYTHONPATH", "")
    if existing:
        path_entries.append(existing)
    if path_entries:
        env["PYTHONPATH"] = os.pathsep.join(path_entries)
    command = [sys.executable, "-m", "unittest", "discover", "-s", str(tests_dir), "-v"]
    try:
        proc = subprocess.run(
            command,
            cwd=str(project_dir),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
        )
        rc = int(proc.returncode)
        stdout_tail = "\n".join(str(proc.stdout or "").splitlines()[-20:])
        stderr_tail = "\n".join(str(proc.stderr or "").splitlines()[-20:])
        status = "pass" if rc == 0 and not import_style_violations else "blocked"
    except subprocess.TimeoutExpired as exc:
        rc = 124
        stdout_tail = "\n".join(str(exc.stdout or "").splitlines()[-20:])
        stderr_tail = "\n".join(str(exc.stderr or "").splitlines()[-20:] + ["generated tests timed out"])
        status = "blocked"
    return {
        "passed": status == "pass",
        "status": status,
        "reason": "" if status == "pass" else "generated tests failed or used an invalid src-layout import style",
        "checked_files": [path.resolve().relative_to(project_dir.resolve()).as_posix() for path in test_files],
        "import_style_violations": import_style_violations,
        "command": " ".join(command),
        "rc": rc,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }
