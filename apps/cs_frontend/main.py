from __future__ import annotations

import argparse

from apps.cs_frontend.bootstrap import bootstrap_frontend


def main() -> int:
    parser = argparse.ArgumentParser(description="CS frontend CLI")
    parser.add_argument("--session-id", default="cli")
    parser.add_argument("--message", required=True)
    args = parser.parse_args()

    handler = bootstrap_frontend()
    event = handler.handle_user_message(session_id=args.session_id, text=args.message, source="cli")
    print(event.reply_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
