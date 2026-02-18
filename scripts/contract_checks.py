
import json
import re
from urllib.parse import unquote
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = [
    ROOT / "specs" / "contract_input" / "project_marker.schema.json",
    ROOT / "specs" / "contract_output" / "graph.schema.json",
    ROOT / "specs" / "contract_output" / "meta_pipeline_graph.schema.json",
    ROOT / "specs" / "contract_output" / "run_events.schema.json",
]

README_MD = ROOT / "README.md"
MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _is_external_link(link: str) -> bool:
    lower = link.lower()
    return (
        lower.startswith("http://")
        or lower.startswith("https://")
        or lower.startswith("mailto:")
        or lower.startswith("tel:")
    )


def check_readme_links() -> None:
    if not README_MD.exists():
        print("[contract_checks] README.md not found (skip readme link check)")
        return

    errors: list[str] = []
    for lineno, line in enumerate(README_MD.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        for raw_link in MD_LINK_RE.findall(line):
            link = raw_link.strip()
            if not link or _is_external_link(link) or link.startswith("#"):
                continue

            path_part = link.split("#", 1)[0].strip()
            if not path_part:
                continue
            path_part = unquote(path_part)
            rel = path_part[1:] if path_part.startswith("/") else path_part
            candidate = (ROOT / rel).resolve()
            if not candidate.exists():
                errors.append(f"README.md:{lineno}: broken link '{raw_link}' -> '{rel}'")

    if errors:
        raise SystemExit(
            "[contract_checks] README contains broken local links:\n"
            + "\n".join(f"- {e}" for e in errors)
        )

    print("[contract_checks] readme links ok")


def check_unique_graph_spider_impl() -> None:
    web_root = ROOT / "web"
    if not web_root.exists():
        print("[contract_checks] web/ not found (skip unique impl check)")
        return

    archive_root = web_root / "_archive"

    violations: list[Path] = []

    # Hard rule: only web/graph_spider owns the real implementation.
    # - No versioned implementation files in web/graph_spider
    # - No extra implementations under web/graph_spider_v*
    # - graph_spider_v2 is allowed as a redirect shell with ONLY index.html
    # - legacy files must live under web/_archive
    for p in web_root.rglob("*"):
        if p.is_dir():
            continue

        # Allow any historical copies under archive.
        if archive_root in p.parents:
            continue

        rel = p.relative_to(ROOT).as_posix()

        # Forbid stray legacy web-root qwebchannel.js placeholder.
        if rel == "web/qwebchannel.js":
            violations.append(p)
            continue

        # Forbid experimental/versioned spider implementations.
        if rel.startswith("web/graph_spider/"):
            name = p.name
            if name == "bootstrap_graph.js":
                violations.append(p)
                continue
            if name.startswith("spider_v") and name.endswith((".js", ".css")):
                violations.append(p)
                continue

        # Enforce graph_spider_v2 is redirect-only.
        if rel.startswith("web/graph_spider_v2/"):
            if rel != "web/graph_spider_v2/index.html":
                violations.append(p)
            continue

        # Forbid any other web/graph_spider_v*/ trees outside _archive.
        if rel.startswith("web/graph_spider_v"):
            violations.append(p)

    if violations:
        formatted = "\n".join(f"- {v.relative_to(ROOT).as_posix()}" for v in sorted(violations))
        raise SystemExit(
            "[contract_checks] unique Graph Spider implementation violated.\n"
            "Move experimental/legacy files under web/_archive/ or delete them:\n"
            f"{formatted}"
        )

    print("[contract_checks] unique Graph Spider implementation ok")

def main():
    missing = [p for p in SCHEMAS if not p.exists()]
    if missing:
        raise SystemExit(f"[contract_checks] missing schema files: {missing}")
    print("[contract_checks] schema presence ok")

    sample_meta = ROOT / "meta" / "pipeline_graph.json"
    if sample_meta.exists():
        data = json.loads(sample_meta.read_text(encoding="utf-8"))
        if "schema_version" not in data:
            raise SystemExit("[contract_checks] meta/pipeline_graph.json missing schema_version")
        print("[contract_checks] meta schema_version ok")
    else:
        print("[contract_checks] meta/pipeline_graph.json not found (ok for fresh project)")

    check_readme_links()
    check_unique_graph_spider_impl()

if __name__ == "__main__":
    main()
