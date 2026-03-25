from __future__ import annotations

import argparse
import json

from apps.project_backend.api.answer_question import answer_question
from apps.project_backend.api.get_result import get_result
from apps.project_backend.api.get_status import get_status
from apps.project_backend.api.submit_job import submit_job
from apps.project_backend.bootstrap import bootstrap_backend


def main() -> int:
    parser = argparse.ArgumentParser(description="Project backend structured API CLI")
    sub = parser.add_subparsers(dest="cmd")

    p_submit = sub.add_parser("submit_job")
    p_submit.add_argument("--payload", default="{}")

    p_answer = sub.add_parser("answer_question")
    p_answer.add_argument("--payload", default="{}")

    p_status = sub.add_parser("get_status")
    p_status.add_argument("--job-id", required=True)

    p_result = sub.add_parser("get_result")
    p_result.add_argument("--job-id", required=True)

    args = parser.parse_args()
    service = bootstrap_backend()

    if args.cmd == "submit_job":
        out = submit_job(service, json.loads(args.payload))
    elif args.cmd == "answer_question":
        out = answer_question(service, json.loads(args.payload))
    elif args.cmd == "get_status":
        out = get_status(service, args.job_id)
    elif args.cmd == "get_result":
        out = get_result(service, args.job_id)
    else:
        parser.print_help()
        return 1

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
