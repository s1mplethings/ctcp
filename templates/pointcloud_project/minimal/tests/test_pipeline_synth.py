import json
import pathlib
import subprocess
import sys


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True)


def test_pipeline_synth(tmp_path: pathlib.Path) -> None:
    fixture = tmp_path / "fixture"
    out = tmp_path / "out"

    make = _run(
        [
            sys.executable,
            "scripts/make_synth_fixture.py",
            "--out",
            str(fixture),
            "--T",
            "12",
            "--H",
            "80",
            "--W",
            "120",
            "--semantics",
        ]
    )
    assert make.returncode == 0, make.stdout + "\n" + make.stderr

    run = _run(
        [
            sys.executable,
            "scripts/run_v2p.py",
            "--fixture",
            str(fixture),
            "--out",
            str(out),
            "--voxel",
            "0.03",
            "--stride",
            "1",
            "--semantics",
        ]
    )
    assert run.returncode == 0, run.stdout + "\n" + run.stderr
    assert (out / "cloud.ply").exists()
    assert (out / "scorecard.json").exists()
    assert (out / "cloud_sem.ply").exists()

    eval_proc = _run(
        [
            sys.executable,
            "scripts/eval_v2p.py",
            "--cloud",
            str(out / "cloud.ply"),
            "--ref",
            str(fixture / "ref_cloud.ply"),
            "--out",
            str(out / "eval.json"),
            "--voxel",
            "0.03",
        ]
    )
    assert eval_proc.returncode == 0, eval_proc.stdout + "\n" + eval_proc.stderr
    assert (out / "eval.json").exists()

    score = json.loads((out / "scorecard.json").read_text(encoding="utf-8"))
    eval_doc = json.loads((out / "eval.json").read_text(encoding="utf-8"))
    assert score["num_frames"] > 0
    assert score["points_down"] > 0
    assert eval_doc["voxel_fscore"] >= 0.8
