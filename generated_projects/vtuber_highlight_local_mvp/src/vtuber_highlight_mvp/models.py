from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class KeywordSignal:
    start: float
    end: float
    text: str


@dataclass(slots=True)
class CandidateSegment:
    start_time: float
    end_time: float
    score: float
    reasons: list[str] = field(default_factory=list)
    transcript_excerpt: str = ""
    output_clip_path: str = ""

    @property
    def duration(self) -> float:
        return max(0.0, self.end_time - self.start_time)

    def to_dict(self) -> dict[str, Any]:
        doc = asdict(self)
        doc["duration"] = round(self.duration, 3)
        doc["score"] = round(float(self.score), 2)
        doc["start_time"] = round(float(self.start_time), 3)
        doc["end_time"] = round(float(self.end_time), 3)
        return doc


@dataclass(slots=True)
class AnalysisResult:
    input_path: str
    output_dir: str
    candidates: list[CandidateSegment]
    duration_seconds: float
    audio_path: str
    timeline_path: str
    report_html: str
    report_json: str
    report_csv: str
    frames_dir: str
    clips_dir: str
    detector_mode: str = "rule_based_audio_plus_keywords"

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_path": self.input_path,
            "output_dir": self.output_dir,
            "duration_seconds": round(float(self.duration_seconds), 3),
            "audio_path": self.audio_path,
            "timeline_path": self.timeline_path,
            "report_html": self.report_html,
            "report_json": self.report_json,
            "report_csv": self.report_csv,
            "frames_dir": self.frames_dir,
            "clips_dir": self.clips_dir,
            "detector_mode": self.detector_mode,
            "candidate_count": len(self.candidates),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


def relative_to(base: Path, target: Path) -> str:
    try:
        return target.resolve().relative_to(base.resolve()).as_posix()
    except Exception:
        return target.as_posix()
