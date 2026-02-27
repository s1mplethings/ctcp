import json
import pathlib
import subprocess
import sys


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True)


def test_smoke(tmp_path: pathlib.Path) -> None:
    fixture = tmp_path / "fixture"
    out = tmp_path / "out"

    make = _run(
        [
            sys.executable,
            "scripts/make_synth_fixture.py",
            "--out",
            str(fixture),
            "--T",
            "8",
            "--H",
            "64",
            "--W",
            "96",
            "--semantics",
        ]
    )
    assert make.returncode == 0, make.stdout + "\n" + make.stderr

    build = _run(
        [
            sys.executable,
            "scripts/run_v2p.py",
            "--fixture",
            str(fixture),
            "--out",
            str(out),
            "--voxel",
            "0.03",
            "--semantics",
        ]
    )
    assert build.returncode == 0, build.stdout + "\n" + build.stderr
    assert (out / "cloud.ply").exists()
    assert (out / "cloud_sem.ply").exists()
    assert (out / "scorecard.json").exists()

    evaluate = _run(
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
    assert evaluate.returncode == 0, evaluate.stdout + "\n" + evaluate.stderr
    eval_doc = json.loads((out / "eval.json").read_text(encoding="utf-8"))
    assert eval_doc["voxel_fscore"] >= 0.8
