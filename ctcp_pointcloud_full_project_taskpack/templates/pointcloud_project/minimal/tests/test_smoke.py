import json, pathlib, subprocess, sys

def test_smoke(tmp_path: pathlib.Path):
    out = tmp_path / "out"
    p = subprocess.run([sys.executable, "scripts/run_v2p.py", "--out", str(out)], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + "\n" + p.stderr
    assert (out / "cloud.ply").exists()
    score = json.loads((out / "scorecard.json").read_text(encoding="utf-8"))
    assert "fps" in score
