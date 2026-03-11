"""Split monolithic CURRENT.md and LAST.md into per-task files.

Usage:
    python scripts/split_task_files.py

Creates:
    meta/tasks/archive/  — one .md per Update section from CURRENT.md
    meta/reports/archive/ — one .md per Update section from LAST.md

The original files are NOT deleted; the caller should replace them with
thin pointer versions after reviewing the output.
"""

import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def slugify(text: str, max_len: int = 60) -> str:
    """Turn a title into a filesystem-safe slug."""
    # Keep ascii, digits, chinese chars, hyphens
    s = text.strip()
    # Replace spaces, slashes, colons with hyphens
    s = re.sub(r"[\s/\\:：（）\(\)\[\]]+", "-", s)
    # Remove anything that isn't alphanumeric, hyphen, underscore, or CJK
    s = re.sub(r"[^\w\u4e00-\u9fff-]", "", s)
    # Collapse multiple hyphens
    s = re.sub(r"-{2,}", "-", s)
    s = s.strip("-")
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s or "untitled"


def split_by_h2(filepath: Path) -> list[tuple[str, str]]:
    """Split markdown into (title, body) pairs by ## headings.

    Returns:
        List of (heading_text, full_section_text_including_heading).
        The first element is the preamble (before any ## Update).
    """
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    sections: list[tuple[str, list[str]]] = []
    current_title = "__preamble__"
    current_lines: list[str] = []

    for line in lines:
        m = re.match(r"^## (Update .+)", line)
        if m:
            # Save previous section
            sections.append((current_title, current_lines))
            current_title = m.group(1).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    # Last section
    sections.append((current_title, current_lines))

    result: list[tuple[str, str]] = []
    for title, lns in sections:
        body = "".join(lns)
        result.append((title, body))

    return result


def write_archive(sections: list[tuple[str, str]], archive_dir: Path, prefix: str) -> list[str]:
    """Write each non-preamble section to archive_dir. Return list of created filenames."""
    archive_dir.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    for title, body in sections:
        if title == "__preamble__":
            continue
        # Extract date from title like "Update 2026-03-08 - ..."
        date_match = re.match(r"Update (\d{4}-\d{2}-\d{2})\s*-?\s*(.*)", title)
        if date_match:
            date_str = date_match.group(1).replace("-", "")
            topic = date_match.group(2).strip()
            slug = slugify(topic) if topic else "update"
            filename = f"{date_str}-{slug}.md"
        else:
            slug = slugify(title)
            filename = f"{slug}.md"

        # Promote ## to # for standalone file
        standalone_body = body
        if standalone_body.startswith("## "):
            standalone_body = "#" + standalone_body[2:]

        filepath = archive_dir / filename
        # Handle duplicates
        if filepath.exists():
            for i in range(2, 100):
                alt = archive_dir / f"{filepath.stem}-{i}.md"
                if not alt.exists():
                    filepath = alt
                    filename = filepath.name
                    break

        filepath.write_text(standalone_body, encoding="utf-8")
        created.append(filename)
        print(f"  {prefix}/{filename}")

    return created


def main() -> None:
    current_path = REPO / "meta" / "tasks" / "CURRENT.md"
    last_path = REPO / "meta" / "reports" / "LAST.md"

    print("=== Splitting CURRENT.md ===")
    current_sections = split_by_h2(current_path)
    preamble_current = ""
    for title, body in current_sections:
        if title == "__preamble__":
            preamble_current = body
            break
    task_archive = REPO / "meta" / "tasks" / "archive"
    created_tasks = write_archive(current_sections, task_archive, "meta/tasks/archive")
    print(f"  → {len(created_tasks)} task files created")

    print("\n=== Splitting LAST.md ===")
    last_sections = split_by_h2(last_path)
    preamble_last = ""
    for title, body in last_sections:
        if title == "__preamble__":
            preamble_last = body
            break
    report_archive = REPO / "meta" / "reports" / "archive"
    created_reports = write_archive(last_sections, report_archive, "meta/reports/archive")
    print(f"  → {len(created_reports)} report files created")

    # Write preambles for reference
    (task_archive / "__preamble__.md").write_text(preamble_current, encoding="utf-8")
    (report_archive / "__preamble__.md").write_text(preamble_last, encoding="utf-8")

    print("\nDone. Review archive dirs, then replace originals with thin pointers.")


if __name__ == "__main__":
    main()
