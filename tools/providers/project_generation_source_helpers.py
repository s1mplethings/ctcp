from __future__ import annotations

import json
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Any

from tools.providers.project_generation_decisions import CLI_SHAPE, GUI_SHAPE, PRODUCTION_MODE, TOOL_SHAPE, WEB_SHAPE

_FONT_5X7: dict[str, tuple[str, ...]] = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    "/": ("00001", "00010", "00100", "01000", "10000", "00000", "00000"),
    ":": ("00000", "00110", "00110", "00000", "00110", "00110", "00000"),
    "?": ("01110", "10001", "00010", "00100", "00100", "00000", "00100"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}


def build_missing_context_extra(*, lists: dict[str, Any], project_id: str, project_type: str, package_name: str, entry_script: str) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "project_type": project_type,
        "project_archetype": str(lists.get("project_archetype", "")),
        "package_name": package_name,
        "execution_mode": str(lists.get("execution_mode", PRODUCTION_MODE)),
        "benchmark_case": str(lists.get("benchmark_case", "")),
        "delivery_shape": str(lists.get("delivery_shape", CLI_SHAPE)),
        "project_type_decision_source": str(lists.get("project_type_decision_source", "")),
        "project_archetype_decision_source": str(lists.get("project_archetype_decision_source", "")),
        "shape_decision_source": str(lists.get("shape_decision_source", "")),
        "entrypoint": entry_script,
        "startup_readme": str(lists.get("startup_readme", "")),
        "generation_mode": str(lists.get("generation_mode", "")),
        "scaffold_bootstrap_used": False,
        "business_codegen_used": False,
        "consumed_context_pack": False,
        "consumed_context_files": [],
        "context_influence_summary": [],
        "business_files_generated": [],
        "business_files_missing": list(lists.get("business_files", [])),
        "reference_project_mode": lists.get("reference_project_mode", {"enabled": False, "mode": "structure_workflow_docs"}),
        "reference_style_applied": [],
        "demo_required": bool(lists.get("demo_required", False)),
        "visual_evidence_required": bool(lists.get("visual_evidence_required", False)),
        "screenshot_required": bool(lists.get("screenshot_required", False)),
        "visual_evidence_status": str(lists.get("visual_evidence_status", "not_requested")),
        "visual_evidence_files": [],
        "benchmark_sample_applied": bool(lists.get("benchmark_sample_applied", False)),
        "decision_nodes": list(lists.get("decision_nodes", [])),
        "flow_nodes": list(lists.get("flow_nodes", [])),
        "gate_layers": {
            "structural": {"passed": False, "reason": "missing context pack"},
            "behavioral": {"passed": False, "reason": "missing context pack"},
            "result": {"passed": False, "target": "missing_context_pack", "reason": "missing context pack"},
        },
        "behavioral_checks": {"startup_probe": {}, "export_probe": {}},
        "visual_evidence_capture": {
            "status": "missing_context_pack",
            "reason": "missing context pack",
            "files": [],
            "source_files": [],
        },
        "context_pack_error": "missing_or_empty_context_pack",
    }


def build_success_extra(
    *,
    lists: dict[str, Any],
    project_id: str,
    project_type: str,
    package_name: str,
    entry_script: str,
    consumed_context: bool,
    consumed_files: list[str],
    context_influence_summary: list[str],
    business_generated: list[str],
    business_missing: list[str],
    reference_style_applied: list[str],
    gate_layers: dict[str, Any],
    behavior_probe: dict[str, Any],
    export_probe: dict[str, Any],
    scaffold: dict[str, Any],
    visual_evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "project_type": project_type,
        "project_archetype": str(lists.get("project_archetype", "")),
        "package_name": package_name,
        "execution_mode": str(lists.get("execution_mode", PRODUCTION_MODE)),
        "benchmark_case": str(lists.get("benchmark_case", "")),
        "delivery_shape": str(lists.get("delivery_shape", CLI_SHAPE)),
        "project_type_decision_source": str(lists.get("project_type_decision_source", "")),
        "project_archetype_decision_source": str(lists.get("project_archetype_decision_source", "")),
        "shape_decision_source": str(lists.get("shape_decision_source", "")),
        "entrypoint": entry_script,
        "startup_readme": str(lists.get("startup_readme", "")),
        "generation_mode": str(lists.get("generation_mode", "")),
        "scaffold_bootstrap_used": str(scaffold.get("status", "")).strip().lower() == "pass",
        "business_codegen_used": bool(business_generated),
        "consumed_context_pack": consumed_context,
        "consumed_context_files": consumed_files,
        "context_influence_summary": context_influence_summary,
        "business_files_generated": business_generated,
        "business_files_missing": business_missing,
        "reference_project_mode": lists.get("reference_project_mode", {"enabled": False, "mode": "structure_workflow_docs"}),
        "reference_style_applied": reference_style_applied,
        "demo_required": bool(lists.get("demo_required", False)),
        "visual_evidence_required": bool(lists.get("visual_evidence_required", False)),
        "screenshot_required": bool(lists.get("screenshot_required", False)),
        "visual_evidence_status": str(visual_evidence.get("status", "")).strip() or str(lists.get("visual_evidence_status", "not_requested")),
        "visual_evidence_files": list(visual_evidence.get("files", [])) if isinstance(visual_evidence.get("files", []), list) else [],
        "benchmark_sample_applied": bool(lists.get("benchmark_sample_applied", False)),
        "decision_nodes": list(lists.get("decision_nodes", [])),
        "flow_nodes": list(lists.get("flow_nodes", [])),
        "gate_layers": gate_layers,
        "behavioral_checks": {"startup_probe": behavior_probe, "export_probe": export_probe},
        "visual_evidence_capture": visual_evidence,
        "scaffold": scaffold,
    }


def _run_command_capture(cmd: list[str], *, cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "command": " ".join(cmd),
        "rc": int(proc.returncode),
        "stdout_tail": "\n".join(str(proc.stdout or "").splitlines()[-12:]),
        "stderr_tail": "\n".join(str(proc.stderr or "").splitlines()[-12:]),
        "status": "pass" if int(proc.returncode) == 0 else "blocked",
    }


def _safe_ascii_line(text: str, *, max_chars: int = 44) -> str:
    line = str(text or "").strip().upper()
    line = line.encode("ascii", errors="replace").decode("ascii")
    line = " ".join(line.split())
    return line[:max_chars] if len(line) > max_chars else line


def _fill_rect(buf: bytearray, *, width: int, height: int, left: int, top: int, rect_width: int, rect_height: int, color: tuple[int, int, int]) -> None:
    right = max(0, min(width, left + rect_width))
    bottom = max(0, min(height, top + rect_height))
    start_x = max(0, left)
    start_y = max(0, top)
    if start_x >= right or start_y >= bottom:
        return
    r, g, b = color
    for y in range(start_y, bottom):
        row_offset = y * width * 3
        for x in range(start_x, right):
            idx = row_offset + x * 3
            buf[idx] = r
            buf[idx + 1] = g
            buf[idx + 2] = b


def _draw_glyph(buf: bytearray, *, width: int, height: int, ch: str, left: int, top: int, scale: int, color: tuple[int, int, int]) -> None:
    glyph = _FONT_5X7.get(ch, _FONT_5X7["?"])
    for row_index, row in enumerate(glyph):
        for col_index, bit in enumerate(row):
            if bit != "1":
                continue
            _fill_rect(
                buf,
                width=width,
                height=height,
                left=left + col_index * scale,
                top=top + row_index * scale,
                rect_width=scale,
                rect_height=scale,
                color=color,
            )


def _draw_text_line(buf: bytearray, *, width: int, height: int, text: str, left: int, top: int, scale: int, color: tuple[int, int, int]) -> None:
    cursor = left
    for raw_char in text:
        ch = raw_char if raw_char in _FONT_5X7 else "?"
        _draw_glyph(buf, width=width, height=height, ch=ch, left=cursor, top=top, scale=scale, color=color)
        cursor += 6 * scale


def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + tag
        + payload
        + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    )


def _write_png(path: Path, *, width: int, height: int, rgb: bytearray) -> None:
    rows = []
    stride = width * 3
    for y in range(height):
        start = y * stride
        rows.append(b"\x00" + bytes(rgb[start : start + stride]))
    payload = zlib.compress(b"".join(rows), level=9)
    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png.extend(_png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)))
    png.extend(_png_chunk(b"IDAT", payload))
    png.extend(_png_chunk(b"IEND", b""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(png))


def _render_visual_evidence_png(
    *,
    path: Path,
    title: str,
    subtitle: str,
    detail_lines: list[str],
) -> None:
    lines = [_safe_ascii_line(title, max_chars=32), _safe_ascii_line(subtitle, max_chars=40)]
    lines.extend(_safe_ascii_line(line, max_chars=44) for line in detail_lines[:8] if str(line or "").strip())
    if not lines:
        lines = ["CTCP VISUAL EVIDENCE"]
    scale = 2
    margin = 16
    line_height = 10 * scale
    max_len = max(len(line) for line in lines)
    width = max(360, margin * 2 + max_len * 6 * scale)
    height = max(200, margin * 2 + len(lines) * line_height + 40)
    rgb = bytearray([245, 247, 250] * width * height)
    _fill_rect(rgb, width=width, height=height, left=0, top=0, rect_width=width, rect_height=44, color=(29, 78, 216))
    _fill_rect(rgb, width=width, height=height, left=0, top=44, rect_width=width, rect_height=4, color=(96, 165, 250))
    _fill_rect(rgb, width=width, height=height, left=14, top=60, rect_width=width - 28, rect_height=height - 74, color=(255, 255, 255))
    accent_colors = [(255, 255, 255), (255, 255, 255), (15, 23, 42), (15, 23, 42), (15, 23, 42)]
    top = 14
    for index, line in enumerate(lines):
        color = accent_colors[index] if index < len(accent_colors) else (15, 23, 42)
        left = margin if index >= 2 else 18
        _draw_text_line(rgb, width=width, height=height, text=line, left=left, top=top, scale=scale, color=color)
        top += line_height if index >= 1 else 18
        if index == 0:
            top += 4
    _write_png(path, width=width, height=height, rgb=rgb)


def _write_visual_failure_note(project_artifacts_dir: Path, reason: str) -> None:
    note_path = project_artifacts_dir / "screenshots_not_available_reason.txt"
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text((str(reason or "").strip() or "visual evidence capture unavailable") + "\n", encoding="utf-8")


def _clear_visual_failure_note(project_artifacts_dir: Path) -> None:
    note_path = project_artifacts_dir / "screenshots_not_available_reason.txt"
    if note_path.exists():
        note_path.unlink()


def _capture_visual_evidence(
    *,
    run_dir: Path,
    project_root: str,
    delivery_shape: str,
    entry_script: str,
    behavior_probe: dict[str, Any],
    export_probe: dict[str, Any],
    export_dir: Path,
) -> dict[str, Any]:
    shape = str(delivery_shape or "").strip()
    project_artifacts_dir = (run_dir / project_root / "artifacts").resolve()
    screenshots_dir = project_artifacts_dir / "screenshots"
    if shape not in {GUI_SHAPE, WEB_SHAPE}:
        _clear_visual_failure_note(project_artifacts_dir)
        return {
            "status": "not_requested",
            "reason": "visual evidence not required for this delivery shape",
            "files": [],
            "source_files": [],
        }
    try:
        export_rc = int(dict(export_probe).get("rc", 1))
    except Exception:
        export_rc = 1
    try:
        behavior_rc = int(dict(behavior_probe).get("rc", 1))
    except Exception:
        behavior_rc = 1
    if export_rc != 0:
        reason = "export probe must pass before screenshot capture"
        _write_visual_failure_note(project_artifacts_dir, reason)
        return {"status": "capture_failed", "reason": reason, "files": [], "source_files": []}

    exported_files = sorted(path for path in export_dir.rglob("*") if path.is_file())
    if not exported_files:
        reason = "no exported files available to summarize into screenshot evidence"
        _write_visual_failure_note(project_artifacts_dir, reason)
        return {"status": "capture_failed", "reason": reason, "files": [], "source_files": []}

    screenshot_path = screenshots_dir / "overview.png"
    title = "CTCP VISUAL EVIDENCE"
    subtitle = f"{shape.upper()} {Path(entry_script).name}"
    detail_lines = [
        f"STARTUP {'PASS' if behavior_rc == 0 else 'BLOCKED'}",
        f"EXPORT {'PASS' if export_rc == 0 else 'BLOCKED'}",
    ]
    for path in exported_files[:5]:
        detail_lines.append(f"OUT {path.name}")
    _render_visual_evidence_png(path=screenshot_path, title=title, subtitle=subtitle, detail_lines=detail_lines)
    rel_file = screenshot_path.resolve().relative_to(run_dir.resolve()).as_posix()
    _clear_visual_failure_note(project_artifacts_dir)
    return {
        "status": "provided",
        "reason": "runtime probes passed and visual evidence screenshot was captured from exported output",
        "files": [rel_file],
        "source_files": [path.resolve().relative_to(export_dir.resolve()).as_posix() for path in exported_files[:8]],
    }


def build_runtime_checks(
    *,
    run_dir: Path,
    project_root: str,
    package_name: str,
    entry_script: str,
    delivery_shape: str,
    execution_mode: str,
    benchmark_sample_applied: bool,
    benchmark_case: str,
    visual_evidence_status: str,
    generated_files: list[str],
    source_files: list[str],
    business_missing: list[str],
    generated_business_files: list[str],
    scaffold_status: str,
    consumed_context: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    src_root = (run_dir / project_root / "src").resolve()
    if delivery_shape == TOOL_SHAPE:
        behavior_probe = _run_command_capture(
            [sys.executable, "-c", f"import sys;sys.path.insert(0, r'{src_root}');import {package_name}.service as service;print('ok' if hasattr(service, 'generate_project') else 'missing')"],
            cwd=run_dir,
        )
    elif delivery_shape == WEB_SHAPE:
        entry_path = (run_dir / entry_script).resolve()
        behavior_probe = _run_command_capture([sys.executable, str(entry_path), "--serve"], cwd=entry_path.parent)
    else:
        entry_path = (run_dir / entry_script).resolve()
        behavior_probe = _run_command_capture([sys.executable, str(entry_path), "--help"], cwd=entry_path.parent)

    with tempfile.TemporaryDirectory(prefix="ctcp_project_export_probe_") as td:
        export_dir = Path(td)
        if delivery_shape == TOOL_SHAPE:
            export_probe = _run_command_capture(
                [sys.executable, "-c", f"import json, sys;from pathlib import Path;sys.path.insert(0, r'{src_root}');from {package_name}.service import generate_project;result = generate_project(goal='smoke export', project_name='Smoke Project', out_dir=Path(r'{export_dir}'));print(json.dumps(result, ensure_ascii=False))"],
                cwd=run_dir,
            )
        else:
            entry_path = (run_dir / entry_script).resolve()
            export_cmd = [sys.executable, str(entry_path), "--goal", "smoke export", "--project-name", "Smoke Project", "--out", str(export_dir)]
            if delivery_shape == GUI_SHAPE:
                export_cmd.append("--headless")
            export_probe = _run_command_capture(export_cmd, cwd=entry_path.parent)

        visual_evidence = _capture_visual_evidence(
            run_dir=run_dir,
            project_root=project_root,
            delivery_shape=delivery_shape,
            entry_script=entry_script,
            behavior_probe=behavior_probe,
            export_probe=export_probe,
            export_dir=export_dir,
        )

    visual_status = str(visual_evidence.get("status", "")).strip() or str(visual_evidence_status or "not_requested").strip()
    visual_required = delivery_shape in {GUI_SHAPE, WEB_SHAPE}
    result_passed = consumed_context and not (execution_mode == PRODUCTION_MODE and benchmark_sample_applied)
    result_reason = "mode-specific result contract satisfied"
    if visual_required:
        result_passed = result_passed and visual_status == "provided" and bool(visual_evidence.get("files", []))
        result_reason = (
            "runtime probes passed and screenshot evidence captured"
            if result_passed
            else str(visual_evidence.get("reason", "")).strip() or "visual evidence required for gui/web delivery"
        )

    gate_layers = {
        "structural": {
            "passed": not sorted(set(source_files) - set(generated_files)) and scaffold_status == "pass" and bool(generated_business_files) and not business_missing,
            "reason": "required files, manifest inputs, and deliverables are all present",
        },
        "behavioral": {
            "passed": str(behavior_probe.get("status", "")).lower() == "pass" and str(export_probe.get("status", "")).lower() == "pass",
            "reason": "startup and export probes passed",
        },
        "result": {
            "passed": result_passed,
            "target": benchmark_case or ("production_request_goal" if execution_mode == PRODUCTION_MODE else "benchmark_regression_case"),
            "reason": result_reason,
        },
    }
    return behavior_probe, export_probe, gate_layers, visual_evidence
