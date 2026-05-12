#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.agent_manifest_generator import generate_manifest_from_file, write_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a CTCP agent manifest from a JSON requirement file.")
    parser.add_argument("--input", required=True, help="Input JSON requirement file")
    parser.add_argument("--output", required=True, help="Output JSON manifest path")
    args = parser.parse_args()

    manifest = generate_manifest_from_file(Path(args.input).resolve())
    write_manifest(Path(args.output).resolve(), manifest)
    print(f"[generate_agent_manifest] output={Path(args.output).resolve().as_posix()}")
    print(f"[generate_agent_manifest] agents={len(manifest.get('agents', []))} tools={len(manifest.get('tools', []))} workflows={len(manifest.get('workflows', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
