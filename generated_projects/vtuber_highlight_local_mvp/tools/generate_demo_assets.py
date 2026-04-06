from __future__ import annotations

import math
import struct
import subprocess
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = PROJECT_ROOT / "demo_assets"
VIDEO_PATH = DEMO_DIR / "sample_vtuber_replay.mp4"
WAV_PATH = DEMO_DIR / "sample_vtuber_replay.wav"
KEYWORDS_PATH = DEMO_DIR / "sample_vtuber_replay.keywords.txt"


def _amplitude_at(second: float) -> tuple[float, float]:
    if 3.0 <= second <= 4.1:
        return 0.75, 900.0
    if 7.2 <= second <= 8.3:
        return 0.92, 1400.0
    if 11.0 <= second <= 12.4:
        return 0.68, 1100.0
    return 0.08, 210.0


def build_demo_wav() -> None:
    sample_rate = 16000
    duration_seconds = 14.0
    total_samples = int(sample_rate * duration_seconds)
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    with wave.open(str(WAV_PATH), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        frames = bytearray()
        for index in range(total_samples):
            second = index / sample_rate
            amplitude, freq = _amplitude_at(second)
            wobble = 0.08 * math.sin(2.0 * math.pi * 3.0 * second)
            burst = amplitude * math.sin(2.0 * math.pi * freq * second)
            harmonic = amplitude * 0.35 * math.sin(2.0 * math.pi * (freq * 1.8) * second)
            sample = max(-0.98, min(0.98, burst + harmonic + wobble))
            frames.extend(struct.pack("<h", int(sample * 32767)))
        handle.writeframes(bytes(frames))


def build_demo_video() -> None:
    lines = [
        "00:00:03.10|笑崩了，直接怪叫",
        "00:00:07.35|这段是鬼叫级反应",
        "00:00:11.25|高能收尾",
    ]
    KEYWORDS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    drawtext = (
        "drawtext=text='VTuber Replay Demo':x=20:y=20:fontsize=26:fontcolor=white,"
        "drawtext=text='calm chat':enable='between(t,0,3)':x=20:y=190:fontsize=30:fontcolor=white,"
        "drawtext=text='laugh burst':enable='between(t,3,4.2)':x=20:y=190:fontsize=30:fontcolor=yellow,"
        "drawtext=text='calm reset':enable='between(t,4.2,7.2)':x=20:y=190:fontsize=30:fontcolor=white,"
        "drawtext=text='scream reaction':enable='between(t,7.2,8.4)':x=20:y=190:fontsize=30:fontcolor=red,"
        "drawtext=text='hype ending':enable='between(t,11,12.5)':x=20:y=190:fontsize=30:fontcolor=lime"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x1f2430:s=640x360:d=14",
            "-i",
            str(WAV_PATH),
            "-vf",
            drawtext,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(VIDEO_PATH),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )


def main() -> int:
    build_demo_wav()
    build_demo_video()
    if WAV_PATH.exists():
        WAV_PATH.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
