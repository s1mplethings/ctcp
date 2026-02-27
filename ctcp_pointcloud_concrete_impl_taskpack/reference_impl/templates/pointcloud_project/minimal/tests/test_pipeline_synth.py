import json, pathlib, subprocess, sys

def test_pipeline_synth(tmp_path: pathlib.Path):
    fixture = tmp_path / "fixture"
    out = tmp_path / "out"
    # make fixture
    p = subprocess.run([sys.executable, "scripts/make_synth_fixture.py", "--out", str(fixture), "--T", "12", "--H", "80", "--W", "120", "--semantics"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + "\n" + p.stderr

    p = subprocess.run([sys.executable, "scripts/run_v2p.py", "--fixture", str(fixture), "--out", str(out), "--voxel", "0.03", "--stride", "1", "--semantics"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + "\n" + p.stderr

    assert (out / "cloud.ply").exists()
    assert (out / "scorecard.json").exists()
    assert (out / "cloud_sem.ply").exists()

    p = subprocess.run([sys.executable, "scripts/eval_v2p.py", "--cloud", str(out/"cloud.ply"), "--ref", str(fixture/"ref_cloud.ply"), "--out", str(out/"eval.json"), "--voxel", "0.03"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + "\n" + p.stderr
    ev = json.loads((out / "eval.json").read_text(encoding="utf-8"))
    assert ev["voxel_fscore"] >= 0.80
