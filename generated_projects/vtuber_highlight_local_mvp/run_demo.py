from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vtuber_highlight_mvp.cli import main


if __name__ == "__main__":
    raise SystemExit(
        main(
            [
                "analyze",
                "--input",
                str(ROOT / "demo_assets" / "sample_vtuber_replay.mp4"),
                "--keywords-file",
                str(ROOT / "demo_assets" / "sample_vtuber_replay.keywords.txt"),
                "--output",
                str(ROOT / "output" / "demo_run"),
                "--export-clips",
            ]
        )
    )
