import json, pathlib, subprocess, sys

def test_scaffold_pointcloud_minimal(tmp_path: pathlib.Path):
    repo = pathlib.Path(".").resolve()
    out = tmp_path / "v2p_project"
    runs = tmp_path / "ctcp_runs"

    cmd = [
        sys.executable, "scripts/ctcp_orchestrate.py", "scaffold-pointcloud",
        "--out", str(out),
        "--name", "v2p_project",
        "--profile", "minimal",
        "--runs-root", str(runs),
        "--dialogue-script", "tests/fixtures/dialogues/scaffold_pointcloud.jsonl",
    ]
    p = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + "\n" + p.stderr

    assert (out / "README.md").exists()
    assert (out / "docs" / "00_CORE.md").exists()
    assert (out / "scripts" / "run_v2p.py").exists()
    assert (out / "tests" / "test_smoke.py").exists()
    assert (out / "meta" / "manifest.json").exists()

    manifest = json.loads((out / "meta" / "manifest.json").read_text(encoding="utf-8"))
    assert "files" in manifest and manifest["files"]
