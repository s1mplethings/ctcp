import pathlib
import subprocess
import sys


def test_clean_project(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "proj"
    root.mkdir(parents=True, exist_ok=True)

    keep = root / "README.md"
    keep.write_text("keep", encoding="utf-8")

    for rel in ("out/a.txt", "fixture/b.txt", "runs/c.txt", "pkg/__pycache__/x.pyc", "pkg/.pytest_cache/v/cache/nodeids"):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/clean_project.py",
            "--root",
            str(root),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    assert keep.exists()
    assert not (root / "out").exists()
    assert not (root / "fixture").exists()
    assert not (root / "runs").exists()
    assert not (root / "pkg" / "__pycache__").exists()
    assert not (root / "pkg" / ".pytest_cache").exists()
