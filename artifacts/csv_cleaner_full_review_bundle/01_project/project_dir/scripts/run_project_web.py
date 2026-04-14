from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from csv_cleaner_web.service import export_demo_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description='CSV cleaner web tool replay entrypoint')
    parser.add_argument('--goal', default='csv cleaner web tool replay')
    parser.add_argument('--project-name', default='CSV Cleaner Studio')
    parser.add_argument('--out', default=str(ROOT / 'generated_output'))
    parser.add_argument('--serve', action='store_true')
    args = parser.parse_args()
    if args.serve:
        print(json.dumps({
            'status': 'ok',
            'project': 'CSV Cleaner Studio',
            'entrypoint': 'app.py',
            'health_url': 'http://127.0.0.1:8008/api/health'
        }, ensure_ascii=False, indent=2))
        return 0
    result = export_demo_bundle(goal=args.goal, project_name=args.project_name, out_dir=Path(args.out))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
