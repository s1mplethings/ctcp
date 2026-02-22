#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-p",
        "test_mock_agent_pipeline.py",
        "-v",
    ]
    proc = subprocess.run(cmd)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
