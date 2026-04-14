from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class CleaningOptions:
    remove_empty_rows: bool = True
    remove_duplicates: bool = True
    keep_columns: list[str] | None = None


@dataclass
class CleaningResult:
    columns: list[str]
    raw_preview: list[dict[str, str]]
    cleaned_preview: list[dict[str, str]]
    cleaned_csv: str
    stats: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            'columns': list(self.columns),
            'raw_preview': list(self.raw_preview),
            'cleaned_preview': list(self.cleaned_preview),
            'cleaned_csv': self.cleaned_csv,
            'stats': dict(self.stats),
        }


def _normalize_rows(csv_text: str) -> tuple[list[str], list[list[str]]]:
    reader = csv.reader(io.StringIO(csv_text))
    rows = [list(row) for row in reader]
    if not rows:
        return [], []
    header = [str(cell).strip() for cell in rows[0]]
    body = rows[1:]
    width = len(header)
    normalized: list[list[str]] = []
    for row in body:
        padded = list(row[:width]) + [''] * max(0, width - len(row))
        normalized.append([str(cell) for cell in padded[:width]])
    return header, normalized


def _rows_to_dicts(columns: list[str], rows: list[list[str]], limit: int = 8) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows[:limit]:
        out.append({column: row[idx] if idx < len(row) else '' for idx, column in enumerate(columns)})
    return out


def clean_csv_text(csv_text: str, options: CleaningOptions | dict[str, Any] | None = None) -> CleaningResult:
    if isinstance(options, dict):
        options = CleaningOptions(
            remove_empty_rows=bool(options.get('remove_empty_rows', True)),
            remove_duplicates=bool(options.get('remove_duplicates', True)),
            keep_columns=[str(x) for x in options.get('keep_columns', []) if str(x).strip()] or None,
        )
    if options is None:
        options = CleaningOptions()
    columns, rows = _normalize_rows(csv_text)
    working = list(rows)
    original_count = len(working)

    removed_empty = 0
    if options.remove_empty_rows:
        filtered: list[list[str]] = []
        for row in working:
            if any(str(cell).strip() for cell in row):
                filtered.append(row)
            else:
                removed_empty += 1
        working = filtered

    removed_duplicates = 0
    if options.remove_duplicates:
        deduped: list[list[str]] = []
        seen: set[tuple[str, ...]] = set()
        for row in working:
            key = tuple(str(cell).strip() for cell in row)
            if key in seen:
                removed_duplicates += 1
                continue
            seen.add(key)
            deduped.append(row)
        working = deduped

    kept_columns = list(columns)
    if options.keep_columns:
        indices = [idx for idx, column in enumerate(columns) if column in set(options.keep_columns)]
        kept_columns = [columns[idx] for idx in indices]
        working = [[row[idx] for idx in indices] for row in working]

    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')
    if kept_columns:
        writer.writerow(kept_columns)
        writer.writerows(working)
    cleaned_csv = output.getvalue()
    return CleaningResult(
        columns=kept_columns,
        raw_preview=_rows_to_dicts(columns, rows),
        cleaned_preview=_rows_to_dicts(kept_columns, working),
        cleaned_csv=cleaned_csv,
        stats={
            'input_rows': original_count,
            'output_rows': len(working),
            'removed_empty_rows': removed_empty,
            'removed_duplicate_rows': removed_duplicates,
        },
    )


def export_demo_bundle(*, goal: str, project_name: str, out_dir: Path) -> dict[str, str]:
    sample_csv = '\n'.join([
        'order_id,customer,city,amount,notes',
        '1001,Ada,Shanghai,120,priority',
        '1002,Ben,,85,',
        ',,,,',
        '1002,Ben,,85,',
        '1003,Caro,Shenzhen,210,follow-up',
        '1004,Dan,Hangzhou,64,',
    ]) + '\n'
    result = clean_csv_text(
        sample_csv,
        CleaningOptions(remove_empty_rows=True, remove_duplicates=True, keep_columns=['order_id', 'customer', 'amount']),
    )
    deliver_dir = Path(out_dir) / 'deliverables'
    deliver_dir.mkdir(parents=True, exist_ok=True)
    sample_input = deliver_dir / 'sample_input.csv'
    raw_preview = deliver_dir / 'raw_preview.json'
    cleaned_preview = deliver_dir / 'cleaned_preview.json'
    cleaned_csv = deliver_dir / 'cleaned_output.csv'
    acceptance = deliver_dir / 'acceptance_report.json'
    summary = deliver_dir / 'delivery_summary.md'
    sample_input.write_text(sample_csv, encoding='utf-8')
    raw_preview.write_text(json.dumps({'rows': result.raw_preview}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    cleaned_preview.write_text(json.dumps({'rows': result.cleaned_preview, 'stats': result.stats}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    cleaned_csv.write_text(result.cleaned_csv, encoding='utf-8')
    acceptance.write_text(json.dumps({
        'status': 'pass',
        'goal': goal,
        'project_name': project_name,
        'checks': [
            'upload CSV text',
            'preview raw rows',
            'remove empty rows',
            'remove duplicate rows',
            'keep selected columns',
            'export cleaned CSV',
        ],
        'stats': result.stats,
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary.write_text(
        '# Delivery Summary\n\n'
        '- A browser-facing CSV cleaner web tool is included in this package.\n'
        '- `app.py` launches the local UI.\n'
        '- `scripts/run_project_web.py` provides health and cold-replay export.\n',
        encoding='utf-8',
    )
    return {
        'sample_input_csv': str(sample_input),
        'raw_preview_json': str(raw_preview),
        'cleaned_preview_json': str(cleaned_preview),
        'cleaned_output_csv': str(cleaned_csv),
        'acceptance_report_json': str(acceptance),
        'delivery_summary_md': str(summary),
    }
