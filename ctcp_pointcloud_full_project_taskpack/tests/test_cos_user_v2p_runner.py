import sys, json, subprocess, pathlib

def test_cos_user_v2p_stub(tmp_path: pathlib.Path):
    repo = pathlib.Path(".").resolve()
    out_root = tmp_path / "v2p_tests"
    runs_root = tmp_path / "ctcp_runs"

    cmd = [
        sys.executable, "scripts/ctcp_orchestrate.py", "cos-user-v2p",
        "--repo", str(repo),  # for stub, using CTCP repo; real usage points to pointcloud repo
        "--project", "v2p_lab",
        "--out-root", str(out_root),
        "--testkit-zip", "tests/fixtures/testkits/stub_ok.zip",
        "--entry", "python run_all.py",
        "--dialogue-script", "tests/fixtures/dialogues/v2p_cos_user.jsonl",
        "--runs-root", str(runs_root),
        "--skip-verify",
    ]
    p = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + "\n" + p.stderr

    cos_root = runs_root / "cos_user_v2p"
    run_dirs = sorted([d for d in cos_root.iterdir() if d.is_dir()])
    assert run_dirs
    run_dir = run_dirs[-1]

    report = json.loads((run_dir / "artifacts" / "v2p_report.json").read_text(encoding="utf-8"))
    run_id = report["run_id"]
    out_dir = out_root / "v2p_lab" / run_id / "out"
    assert (out_dir / "scorecard.json").exists()
    assert (out_dir / "eval.json").exists()
    assert (out_dir / "cloud.ply").exists()
