from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1] / "generated_projects" / "vtuber_highlight_local_mvp"
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

_IMPORT_ERROR = ""
try:
    from vtuber_highlight_mvp.pipeline import analyze_video
except Exception as exc:  # pragma: no cover - test skip guard
    analyze_video = None  # type: ignore[assignment]
    _IMPORT_ERROR = str(exc)


class GeneratedVtuberHighlightLocalMvpTests(unittest.TestCase):
    def test_smoke_analysis_exports_clip_and_reports(self) -> None:
        if analyze_video is None or not PROJECT_ROOT.exists():
            self.skipTest(f"generated vtuber mvp fixture unavailable: {_IMPORT_ERROR or PROJECT_ROOT}")
        with tempfile.TemporaryDirectory() as td:
            result = analyze_video(
                input_path=PROJECT_ROOT / "demo_assets" / "sample_vtuber_replay.mp4",
                keywords_file=PROJECT_ROOT / "demo_assets" / "sample_vtuber_replay.keywords.txt",
                output_dir=Path(td),
                export_clips=True,
            )
            self.assertGreaterEqual(len(result.candidates), 1)
            self.assertTrue(Path(result.report_html).exists())
            self.assertTrue(Path(result.report_json).exists())
            self.assertTrue(Path(result.report_csv).exists())
            self.assertTrue(Path(result.timeline_path).exists())
            clips = sorted((Path(td) / "clips").glob("*.mp4"))
            self.assertGreaterEqual(len(clips), 1)


if __name__ == "__main__":
    unittest.main()
