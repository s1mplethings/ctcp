from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .config import load_config
from .detection import detect_candidates
from .keywords import load_keyword_signals
from .media import export_clip, extract_audio, extract_frame, ffprobe_duration
from .models import AnalysisResult, relative_to
from .reporting import draw_timeline, write_csv_report, write_html_report, write_json_report


def _default_keyword_path(video_path: Path) -> Path | None:
    candidate = video_path.with_suffix(".keywords.txt")
    return candidate if candidate.exists() else None


def analyze_video(
    *,
    input_path: str | Path,
    output_dir: str | Path,
    export_clips: bool = False,
    keywords_file: str | Path | None = None,
    config_path: str | Path | None = None,
) -> AnalysisResult:
    video_path = Path(input_path).resolve()
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = out_dir / "audio"
    clips_dir = out_dir / "clips"
    frames_dir = out_dir / "frames"
    audio_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(config_path)
    duration = ffprobe_duration(video_path)
    wav_path = audio_dir / f"{video_path.stem}.wav"
    extract_audio(video_path, wav_path, sample_rate=int(config["sample_rate"]))
    keyword_path = Path(keywords_file) if keywords_file else _default_keyword_path(video_path)
    keyword_signals = load_keyword_signals(keyword_path)
    candidates, score_trace = detect_candidates(wav_path, duration, config, keyword_signals)

    for index, candidate in enumerate(candidates, start=1):
        frame_path = frames_dir / f"candidate_{index:02d}.png"
        extract_frame(video_path, (candidate.start_time + candidate.end_time) / 2, frame_path)
        if export_clips:
            clip_path = clips_dir / f"clip_{index:02d}_{candidate.start_time:.2f}_{candidate.end_time:.2f}.mp4"
            export_clip(video_path, candidate.start_time, candidate.end_time, clip_path)
            candidate.output_clip_path = relative_to(out_dir, clip_path)

    timeline_path = out_dir / "timeline.png"
    draw_timeline(score_trace["times"], score_trace["scores"], candidates, timeline_path)
    result = AnalysisResult(
        input_path=video_path.as_posix(),
        output_dir=out_dir.as_posix(),
        candidates=candidates,
        duration_seconds=duration,
        audio_path=wav_path.as_posix(),
        timeline_path=timeline_path.as_posix(),
        report_html=(out_dir / "report.html").as_posix(),
        report_json=(out_dir / "candidates.json").as_posix(),
        report_csv=(out_dir / "candidates.csv").as_posix(),
        frames_dir=frames_dir.as_posix(),
        clips_dir=clips_dir.as_posix(),
    )
    write_json_report(result, Path(result.report_json))
    write_csv_report(result.candidates, Path(result.report_csv))
    write_html_report(result, Path(result.report_html))
    return result
