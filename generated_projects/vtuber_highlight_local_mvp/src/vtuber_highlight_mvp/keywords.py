from __future__ import annotations

import re
from pathlib import Path

from .models import KeywordSignal

TIME_RE = re.compile(r"^(?P<stamp>\d{2}:\d{2}:\d{2}(?:\.\d+)?)\|(?P<text>.+)$")


def parse_timestamp(value: str) -> float:
    parts = value.strip().split(":")
    hours, minutes, seconds = int(parts[0]), int(parts[1]), float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def load_keyword_signals(path: str | Path | None) -> list[KeywordSignal]:
    if not path:
        return []
    keyword_path = Path(path)
    if not keyword_path.exists():
        return []
    rows: list[KeywordSignal] = []
    for raw_line in keyword_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = TIME_RE.match(line)
        if not match:
            continue
        start = parse_timestamp(match.group("stamp"))
        text = match.group("text").strip()
        rows.append(KeywordSignal(start=max(0.0, start - 0.4), end=start + 0.9, text=text))
    return rows


def matching_keywords(start_time: float, end_time: float, signals: list[KeywordSignal]) -> list[str]:
    hits: list[str] = []
    for signal in signals:
        if signal.end < start_time or signal.start > end_time:
            continue
        hits.append(signal.text)
    return hits
