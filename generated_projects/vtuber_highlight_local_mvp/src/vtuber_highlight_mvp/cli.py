from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vtuber_highlight_mvp.pipeline import analyze_video


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect VTuber-style high-energy highlight clips from local replay videos")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="analyze one local video")
    analyze.add_argument("--input", required=True, help="local video file path")
    analyze.add_argument("--output", required=True, help="output directory")
    analyze.add_argument("--keywords-file", default="", help="optional timestamped keyword sidecar")
    analyze.add_argument("--config", default="", help="optional config json path")
    analyze.add_argument("--export-clips", action="store_true", help="export clip files with ffmpeg")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        result = analyze_video(
            input_path=args.input,
            output_dir=args.output,
            export_clips=bool(args.export_clips),
            keywords_file=args.keywords_file or None,
            config_path=args.config or None,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
