from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "demo_run"
SCREENSHOTS_DIR = PROJECT_ROOT / "demo_assets" / "screenshots"
GIF_PATH = PROJECT_ROOT / "demo_assets" / "demo_walkthrough.gif"


def _load_default_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def _panel_base(title: str, subtitle: str, size: tuple[int, int] = (1280, 720)) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", size, color=(245, 247, 252))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((30, 30, size[0] - 30, size[1] - 30), radius=28, fill=(255, 255, 255), outline=(223, 228, 238))
    title_font = _load_default_font(34)
    subtitle_font = _load_default_font(20)
    draw.text((70, 65), title, fill=(31, 36, 48), font=title_font)
    draw.text((70, 112), subtitle, fill=(92, 101, 122), font=subtitle_font)
    return image, draw


def _fit_image(source: Image.Image, box: tuple[int, int]) -> Image.Image:
    target_w, target_h = box
    ratio = min(target_w / source.width, target_h / source.height)
    new_size = (max(1, int(source.width * ratio)), max(1, int(source.height * ratio)))
    return source.resize(new_size)


def _save_candidate_three_frame() -> Path:
    source = OUTPUT_DIR / "frames" / "candidate_03.png"
    target = SCREENSHOTS_DIR / "candidate_03_frame.png"
    shutil.copyfile(source, target)
    return target


def _build_report_summary(candidates: list[dict[str, object]], detector_mode: str) -> Path:
    image, draw = _panel_base(
        "VTuber Highlight Demo Summary",
        f"Real run result from output/demo_run | detector={detector_mode}",
    )
    label_font = _load_default_font(22)
    text_font = _load_default_font(18)
    draw.rounded_rectangle((70, 165, 1210, 260), radius=18, fill=(240, 244, 255))
    draw.text((95, 190), f"Candidates detected: {len(candidates)}", fill=(30, 64, 175), font=label_font)
    draw.text((95, 225), "Each row is rendered from candidates.json and exported clips.", fill=(70, 82, 102), font=text_font)

    top = 295
    row_height = 115
    for index, candidate in enumerate(candidates, start=1):
        y0 = top + (index - 1) * row_height
        y1 = y0 + 92
        draw.rounded_rectangle((85, y0, 1195, y1), radius=16, fill=(250, 251, 254), outline=(230, 234, 242))
        score = float(candidate["score"])
        start_time = float(candidate["start_time"])
        end_time = float(candidate["end_time"])
        reasons = " / ".join(candidate.get("reasons", []))
        excerpt = str(candidate.get("transcript_excerpt") or "-")
        draw.text((110, y0 + 14), f"C{index}  {start_time:.2f}s - {end_time:.2f}s", fill=(31, 36, 48), font=label_font)
        draw.text((420, y0 + 14), f"Score {score:.1f}", fill=(201, 79, 18), font=label_font)
        draw.text((110, y0 + 48), reasons, fill=(74, 82, 99), font=text_font)
        draw.text((110, y0 + 71), f"Keyword/Text: {excerpt}", fill=(74, 82, 99), font=text_font)

    out_path = SCREENSHOTS_DIR / "report_summary.png"
    image.save(out_path)
    return out_path


def _build_output_overview(candidates: list[dict[str, object]]) -> Path:
    image, draw = _panel_base(
        "Output Folder Overview",
        "Files below are real artifacts produced by the demo run",
    )
    label_font = _load_default_font(22)
    text_font = _load_default_font(18)
    box_left = 85
    box_width = 520
    box_gap = 40
    panel_top = 170
    panel_bottom = 635

    left_box = (box_left, panel_top, box_left + box_width, panel_bottom)
    right_box = (box_left + box_width + box_gap, panel_top, box_left + box_width * 2 + box_gap, panel_bottom)
    draw.rounded_rectangle(left_box, radius=18, fill=(248, 250, 255), outline=(229, 234, 244))
    draw.rounded_rectangle(right_box, radius=18, fill=(248, 250, 255), outline=(229, 234, 244))
    draw.text((left_box[0] + 25, left_box[1] + 20), "Generated files", fill=(31, 36, 48), font=label_font)
    draw.text((right_box[0] + 25, right_box[1] + 20), "Exported clips", fill=(31, 36, 48), font=label_font)

    files = [
        "report.html",
        "candidates.json",
        "candidates.csv",
        "timeline.png",
        "frames/candidate_01.png",
        "frames/candidate_02.png",
        "frames/candidate_03.png",
    ]
    for index, entry in enumerate(files, start=1):
        draw.text((left_box[0] + 28, left_box[1] + 68 + index * 36), f"- {entry}", fill=(71, 81, 99), font=text_font)

    for index, candidate in enumerate(candidates, start=1):
        clip_path = str(candidate.get("output_clip_path") or "-")
        draw.text((right_box[0] + 28, right_box[1] + 68 + index * 48), f"- {clip_path}", fill=(71, 81, 99), font=text_font)

    draw.text((right_box[0] + 28, right_box[1] + 300), "These clips are cut by ffmpeg from the input replay.", fill=(92, 101, 122), font=text_font)

    out_path = SCREENSHOTS_DIR / "output_overview.png"
    image.save(out_path)
    return out_path


def _build_walkthrough_gif(image_paths: list[Path]) -> Path:
    slides: list[Image.Image] = []
    caption_font = _load_default_font(26)
    for index, path in enumerate(image_paths, start=1):
        source = Image.open(path).convert("RGB")
        canvas, draw = _panel_base(
            "Walkthrough",
            f"Step {index}/{len(image_paths)} | derived from real demo artifacts",
        )
        fitted = _fit_image(source, (1120, 500))
        offset = ((canvas.width - fitted.width) // 2, 165 + math.floor((500 - fitted.height) / 2))
        canvas.paste(fitted, offset)
        draw.rounded_rectangle((70, 635, 1210, 685), radius=14, fill=(240, 244, 255))
        draw.text((95, 648), path.name, fill=(31, 36, 48), font=caption_font)
        slides.append(canvas)

    first, *rest = slides
    first.save(
        GIF_PATH,
        save_all=True,
        append_images=rest,
        duration=1200,
        loop=0,
    )
    return GIF_PATH


def main() -> int:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    report_json = OUTPUT_DIR / "candidates.json"
    if not report_json.exists():
        raise FileNotFoundError(f"Missing demo output: {report_json}")
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    candidates = payload["candidates"]

    _save_candidate_three_frame()
    summary_path = _build_report_summary(candidates, str(payload["detector_mode"]))
    overview_path = _build_output_overview(candidates)

    timeline_src = OUTPUT_DIR / "timeline.png"
    timeline_target = SCREENSHOTS_DIR / "timeline_overview.png"
    if timeline_src != timeline_target:
        shutil.copyfile(timeline_src, timeline_target)

    image_paths = [
        SCREENSHOTS_DIR / "timeline_overview.png",
        summary_path,
        SCREENSHOTS_DIR / "candidate_01_frame.png",
        SCREENSHOTS_DIR / "candidate_02_frame.png",
        SCREENSHOTS_DIR / "candidate_03_frame.png",
        overview_path,
    ]
    _build_walkthrough_gif(image_paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
