from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from http_mvp_spec_workflow_plan_acceptance_json_heal.service import generate_project

def main() -> int:
    parser = argparse.ArgumentParser(description="Web service launcher.")
    parser.add_argument("--goal", default="project generation request")
    parser.add_argument("--project-name", default="Project Copilot")
    parser.add_argument("--out", default=str(ROOT / "generated_output"))
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    if args.serve:
        from importlib import import_module
        payload = import_module('http_mvp_spec_workflow_plan_acceptance_json_heal.app').health_payload()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    result = generate_project(goal=args.goal, project_name=args.project_name, out_dir=Path(args.out))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
