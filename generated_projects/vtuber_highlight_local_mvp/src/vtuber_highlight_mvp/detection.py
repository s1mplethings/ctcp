from __future__ import annotations

import math
import wave
from pathlib import Path
from typing import Any

import numpy as np

from .keywords import matching_keywords
from .models import CandidateSegment, KeywordSignal


def _window_metrics(samples: np.ndarray, sample_rate: int, window_size: int, hop_size: int) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    if len(samples) < window_size:
        return metrics
    for start in range(0, len(samples) - window_size + 1, hop_size):
        frame = samples[start : start + window_size]
        center = (start + window_size / 2) / sample_rate
        rms = float(np.sqrt(np.mean(np.square(frame))))
        peak = float(np.max(np.abs(frame)))
        crossings = np.count_nonzero(np.diff(np.signbit(frame)))
        zcr = float(crossings / max(1, len(frame)))
        spectrum = np.abs(np.fft.rfft(frame))
        total_spec = float(np.sum(spectrum)) or 1e-6
        freqs = np.fft.rfftfreq(len(frame), d=1 / sample_rate)
        high_freq = float(np.sum(spectrum[freqs >= 2200]) / total_spec)
        metrics.append(
            {
                "start": start / sample_rate,
                "end": (start + window_size) / sample_rate,
                "center": center,
                "rms": rms,
                "peak": peak,
                "zcr": zcr,
                "high_freq": high_freq,
            }
        )
    return metrics


def _normalize(values: list[float]) -> np.ndarray:
    raw = np.asarray(values, dtype=np.float32)
    if raw.size == 0:
        return raw
    lo = float(np.percentile(raw, 50))
    hi = float(np.percentile(raw, 95))
    if hi <= lo:
        hi = lo + 1e-6
    return np.clip((raw - lo) / (hi - lo), 0.0, 1.25)


def _group_active_ranges(active: list[bool], metrics: list[dict[str, Any]]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start_idx: int | None = None
    for idx, flag in enumerate(active):
        if flag and start_idx is None:
            start_idx = idx
        if start_idx is not None and (idx == len(active) - 1 or not active[idx + 1]):
            end_idx = idx
            ranges.append((start_idx, end_idx))
            start_idx = None
    return ranges


def _merge_segments(segments: list[CandidateSegment], merge_gap: float, minimum_score: float) -> list[CandidateSegment]:
    merged: list[CandidateSegment] = []
    for segment in sorted(segments, key=lambda item: item.start_time):
        if segment.score < minimum_score:
            continue
        if not merged:
            merged.append(segment)
            continue
        previous = merged[-1]
        if segment.start_time - previous.end_time <= merge_gap:
            previous.end_time = max(previous.end_time, segment.end_time)
            previous.score = max(previous.score, segment.score)
            previous.reasons = sorted(set(previous.reasons + segment.reasons))
            if segment.transcript_excerpt and segment.transcript_excerpt not in previous.transcript_excerpt:
                previous.transcript_excerpt = " / ".join(
                    filter(None, [previous.transcript_excerpt, segment.transcript_excerpt])
                )
        else:
            merged.append(segment)
    return merged


def detect_candidates(
    wav_path: Path,
    duration_seconds: float,
    config: dict[str, Any],
    keyword_signals: list[KeywordSignal] | None = None,
) -> tuple[list[CandidateSegment], dict[str, list[float]]]:
    keyword_signals = keyword_signals or []
    with wave.open(str(wav_path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        frames = wav_file.readframes(wav_file.getnframes())
    if sample_width != 2:
        raise RuntimeError("only 16-bit PCM audio is supported in the MVP")
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    window_size = int(sample_rate * float(config["window_seconds"]))
    hop_size = int(sample_rate * float(config["hop_seconds"]))
    metrics = _window_metrics(samples, sample_rate, window_size, hop_size)
    if not metrics:
        return [], {"times": [], "scores": []}

    rms_norm = _normalize([float(item["rms"]) for item in metrics])
    peak_norm = _normalize([float(item["peak"]) for item in metrics])
    zcr_norm = _normalize([float(item["zcr"]) for item in metrics])
    hf_norm = _normalize([float(item["high_freq"]) for item in metrics])
    weights = dict(config["weights"])

    scores: list[float] = []
    active: list[bool] = []
    for idx, item in enumerate(metrics):
        keyword_hits = matching_keywords(item["start"], item["end"], keyword_signals)
        keyword_bonus = float(config["keyword_bonus"]) if keyword_hits else 0.0
        score = (
            float(weights["rms"]) * float(rms_norm[idx])
            + float(weights["peak"]) * float(peak_norm[idx])
            + float(weights["high_freq"]) * float(hf_norm[idx])
            + float(weights["zcr"]) * float(zcr_norm[idx])
            + keyword_bonus
        )
        scores.append(score)
        active.append(score >= 0.52 or peak_norm[idx] >= 0.88 or (keyword_hits and score >= 0.42))

    raw_segments: list[CandidateSegment] = []
    minimum_segment_seconds = float(config["minimum_segment_seconds"])
    pad_before = float(config["pad_before_seconds"])
    pad_after = float(config["pad_after_seconds"])
    for start_idx, end_idx in _group_active_ranges(active, metrics):
        start_time = max(0.0, float(metrics[start_idx]["start"]) - pad_before)
        end_time = min(duration_seconds, float(metrics[end_idx]["end"]) + pad_after)
        if end_time - start_time < minimum_segment_seconds:
            continue
        segment_slice = slice(start_idx, end_idx + 1)
        segment_scores = scores[segment_slice]
        segment_peak = float(np.max(peak_norm[segment_slice]))
        segment_rms = float(np.max(rms_norm[segment_slice]))
        segment_hf = float(np.max(hf_norm[segment_slice]))
        reasons: list[str] = []
        if segment_rms >= 0.55:
            reasons.append("音量突增")
        if segment_peak >= 0.72:
            reasons.append("峰值明显")
        if segment_hf >= 0.55:
            reasons.append("高频尖锐反应")
        overlap_keywords = matching_keywords(start_time, end_time, keyword_signals)
        transcript_excerpt = " / ".join(overlap_keywords[:2])
        if overlap_keywords:
            reasons.append("关键词增强")
        score_100 = min(100.0, max(0.0, float(np.max(segment_scores) * 100.0)))
        raw_segments.append(
            CandidateSegment(
                start_time=round(start_time, 3),
                end_time=round(end_time, 3),
                score=round(score_100, 2),
                reasons=reasons or ["高能波动"],
                transcript_excerpt=transcript_excerpt,
            )
        )

    merged = _merge_segments(
        raw_segments,
        merge_gap=float(config["merge_gap_seconds"]),
        minimum_score=float(config["minimum_candidate_score"]),
    )
    merged = sorted(merged, key=lambda item: (-item.score, item.start_time))[: int(config["max_candidates"])]
    merged = sorted(merged, key=lambda item: item.start_time)
    return merged, {"times": [float(item["center"]) for item in metrics], "scores": scores}
