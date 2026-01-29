from __future__ import annotations
import os
from pathlib import Path
from .util import iter_files, read_text, write_json, sha1_of_files

PATTERNS_QT = ["Qt6", "Qt5", "QApplication", "QMainWindow", "QWidget"]
PATTERNS_WEBENGINE = ["QWebEngineView", "Qt6::WebEngineWidgets", "Qt5::WebEngineWidgets", "QtWebEngineWidgets", "qtwebengine", "QWebChannel", "qt.webChannelTransport"]

def scan_repo(target: str) -> dict:
    root = Path(target).resolve()
    files = list(iter_files(root))
    rels = [str(p.relative_to(root)).replace("\\","/") for p in files]

    # build system heuristics
    has_cmake = (root / "CMakeLists.txt").exists()
    has_qmake = any(p.suffix == ".pro" for p in files)
    has_pyproject = (root / "pyproject.toml").exists()
    has_package_json = (root / "package.json").exists()

    build_system = "unknown"
    if has_cmake: build_system = "cmake"
    elif has_qmake: build_system = "qmake"
    elif has_pyproject: build_system = "python"
    elif has_package_json: build_system = "node"

    text_hits = set()
    # limited scan for keywords
    for p in files:
        name = p.name.lower()
        if any(name.endswith(ext) for ext in [".cpp",".h",".hpp",".cxx",".cmake",".txt",".md",".pro",".qml",".js",".html",".css"]):
            t = read_text(p)
            for kw in PATTERNS_QT + PATTERNS_WEBENGINE:
                if kw in t:
                    text_hits.add(kw)
    has_qt = any(k in text_hits for k in PATTERNS_QT)
    has_qt_webengine = any(k in text_hits for k in PATTERNS_WEBENGINE)

    # web root candidates
    web_roots = []
    for cand in ["web","resources/web","resources","assets/web","public","static"]:
        if (root / cand).exists():
            web_roots.append(cand.replace("\\","/"))

    # entry candidates for webengine integration
    entry_candidates = []
    for p in files:
        if p.suffix.lower() in [".cpp",".h",".hpp"]:
            t = read_text(p)
            if "QWebEngineView" in t or "QWebChannel" in t:
                entry_candidates.append(str(p.relative_to(root)).replace("\\","/"))
    entry_candidates = entry_candidates[:20]

    profile = {
        "target": str(root),
        "build_system": build_system,
        "has_qt": bool(has_qt),
        "has_qt_webengine": bool(has_qt_webengine),
        "text_hits": sorted(text_hits),
        "web_roots": web_roots,
        "entry_candidates": entry_candidates,
        "file_count": len(files),
        "fingerprint": sha1_of_files(rels),
    }
    return profile

def main():
    import argparse, datetime, json
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--out", default="out_scan")
    args = ap.parse_args()

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    profile = scan_repo(args.target)

    scanned_at = datetime.datetime.utcnow().isoformat() + "Z"
    report = {"scanned_at": scanned_at, "profile": profile, "findings": []}
    write_json(out / "report.json", report)
    (out / "report.md").write_text(
        f"# Scan Report\n\n- target: {profile['target']}\n- scanned_at: {scanned_at}\n\n"
        f"## Profile\n- build_system: {profile['build_system']}\n- has_qt: {profile['has_qt']}\n"
        f"- has_qt_webengine: {profile['has_qt_webengine']}\n- web_roots: {profile['web_roots']}\n"
        f"- entry_candidates: {profile['entry_candidates']}\n\n"
        f"## Text hits\n{', '.join(profile['text_hits'])}\n",
        encoding="utf-8"
    )
    print(str(out / "report.json"))

if __name__ == "__main__":
    main()
