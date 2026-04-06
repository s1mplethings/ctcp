from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vtuber_highlight_mvp.pipeline import analyze_video


class PipelineTests(unittest.TestCase):
    def test_sample_video_produces_candidates_and_reports(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = analyze_video(
                input_path=ROOT / "demo_assets" / "sample_vtuber_replay.mp4",
                keywords_file=ROOT / "demo_assets" / "sample_vtuber_replay.keywords.txt",
                output_dir=Path(td),
                export_clips=False,
            )
            self.assertGreaterEqual(len(result.candidates), 2)
            self.assertTrue(Path(result.report_html).exists())
            self.assertTrue(Path(result.report_json).exists())
            self.assertTrue(Path(result.timeline_path).exists())


if __name__ == "__main__":
    unittest.main()
