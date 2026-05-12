#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.agent_manifest_consumer import generate_agent_scaffold, result_to_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a CTCP agent scaffold from an agent manifest")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--force", action="store_true", help="Replace an existing CTCP-generated scaffold directory")
    args = parser.parse_args()
    try:
        result = generate_agent_scaffold(Path(args.manifest), Path(args.output_dir), force=bool(args.force))
    except Exception as exc:
        print(f"[generate_agent_scaffold][error] {exc}", file=sys.stderr)
        return 2
    print(result_to_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
