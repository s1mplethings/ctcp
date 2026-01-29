from __future__ import annotations
import argparse
from pathlib import Path
from .scan_repo import main as scan_main
from .recommend import main as recommend_main
from .build_bundle import main as bundle_main

def main():
    ap = argparse.ArgumentParser(prog="ai_apply")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("scan")
    p1.add_argument("target")
    p1.add_argument("--out", default="out_scan")

    p2 = sub.add_parser("recommend")
    p2.add_argument("report_json")
    p2.add_argument("--repo-root", default=".")

    p3 = sub.add_parser("bundle")
    p3.add_argument("target_repo")
    p3.add_argument("--recipe", required=True)
    p3.add_argument("--out", required=True)
    p3.add_argument("--repo-root", default=".")

    args, rest = ap.parse_known_args()
    if args.cmd == "scan":
        import sys
        sys.argv = ["scan_repo.py", args.target, "--out", args.out]
        scan_main()
    elif args.cmd == "recommend":
        import sys
        sys.argv = ["recommend.py", args.report_json, "--repo-root", args.repo_root]
        recommend_main()
    elif args.cmd == "bundle":
        import sys
        sys.argv = ["build_bundle.py", args.target_repo, "--recipe", args.recipe, "--out", args.out, "--repo-root", args.repo_root]
        bundle_main()

if __name__ == "__main__":
    main()
