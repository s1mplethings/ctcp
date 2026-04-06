from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt

from .models import AnalysisResult, CandidateSegment, relative_to


def write_json_report(result: AnalysisResult, out_path: Path) -> Path:
    out_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def write_csv_report(candidates: list[CandidateSegment], out_path: Path) -> Path:
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["start_time", "end_time", "duration", "score", "reasons", "transcript_excerpt", "output_clip_path"],
        )
        writer.writeheader()
        for candidate in candidates:
            doc = candidate.to_dict()
            doc["reasons"] = " / ".join(candidate.reasons)
            writer.writerow(doc)
    return out_path


def draw_timeline(score_times: list[float], score_values: list[float], candidates: list[CandidateSegment], out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.plot(score_times, score_values, color="#1f77b4", linewidth=1.5, label="window score")
    for index, candidate in enumerate(candidates, start=1):
        ax.axvspan(candidate.start_time, candidate.end_time, color="#ff7f0e", alpha=0.2)
        ax.text(candidate.start_time, 1.02, f"C{index}", fontsize=8, color="#c45d00")
    ax.set_ylim(0, max(1.05, max(score_values, default=0.0) + 0.1))
    ax.set_xlabel("seconds")
    ax.set_ylabel("score")
    ax.set_title("VTuber high-energy candidate timeline")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path


def write_html_report(result: AnalysisResult, out_path: Path) -> Path:
    base = Path(result.output_dir)
    timeline_rel = relative_to(base, Path(result.timeline_path))
    rows = []
    for index, candidate in enumerate(result.candidates, start=1):
        clip_text = candidate.output_clip_path or "-"
        rows.append(
            f"""
            <tr>
              <td>{index}</td>
              <td>{candidate.start_time:.2f}</td>
              <td>{candidate.end_time:.2f}</td>
              <td>{candidate.duration:.2f}</td>
              <td>{candidate.score:.1f}</td>
              <td>{'<br>'.join(candidate.reasons)}</td>
              <td>{candidate.transcript_excerpt or '-'}</td>
              <td>{clip_text}</td>
            </tr>
            """
        )
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>VTuber Highlight MVP Report</title>
  <style>
    body {{ font-family: "Segoe UI", sans-serif; margin: 24px; background: #f6f7fb; color: #1f2430; }}
    .card {{ background: white; border-radius: 16px; padding: 20px; margin-bottom: 18px; box-shadow: 0 10px 30px rgba(31,36,48,0.08); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #e6e8ef; padding: 10px 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f2f5ff; }}
    .metric {{ display: inline-block; margin-right: 18px; font-weight: 600; }}
    img {{ max-width: 100%; border-radius: 12px; }}
    code {{ background: #eef2ff; padding: 2px 6px; border-radius: 6px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>VTuber Highlight Local MVP</h1>
    <p>输入视频：<code>{result.input_path}</code></p>
    <p>
      <span class="metric">模式：{result.detector_mode}</span>
      <span class="metric">时长：{result.duration_seconds:.2f}s</span>
      <span class="metric">候选数：{len(result.candidates)}</span>
    </p>
  </div>
  <div class="card">
    <h2>时间轴</h2>
    <img src="{timeline_rel}" alt="timeline">
  </div>
  <div class="card">
    <h2>候选清单</h2>
    <table>
      <thead>
        <tr>
          <th>#</th><th>开始</th><th>结束</th><th>时长</th><th>分数</th><th>理由</th><th>关键词/文本</th><th>导出 clip</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")
    return out_path
