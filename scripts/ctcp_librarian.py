#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LAST_RUN_POINTER = ROOT / "meta" / "run_pointers" / "LAST_RUN.txt"
# BEHAVIOR_ID: B033

try:
    from tools.run_paths import get_repo_slug
    from tools.librarian_context_pack import LibrarianContractError, build_context_pack, write_failure_doc
    from tools.run_manifest import update_librarian_context
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(ROOT))
    from tools.run_paths import get_repo_slug
    from tools.librarian_context_pack import LibrarianContractError, build_context_pack, write_failure_doc
    from tools.run_manifest import update_librarian_context


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _resolve_run_dir(raw: str) -> Path:
    if raw.strip():
        run_dir = Path(raw).expanduser().resolve()
    else:
        if not LAST_RUN_POINTER.exists():
            raise SystemExit("[ctcp_librarian] missing LAST_RUN pointer; pass --run-dir")
        pointed = LAST_RUN_POINTER.read_text(encoding="utf-8").strip()
        if not pointed:
            raise SystemExit("[ctcp_librarian] LAST_RUN pointer is empty; pass --run-dir")
        run_dir = Path(pointed).expanduser().resolve()
    if _is_within(run_dir, ROOT):
        raise SystemExit(f"[ctcp_librarian] run_dir must be outside repo: {run_dir}")
    return run_dir


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _build_context_pack(file_request: dict[str, Any]) -> dict[str, Any]:
    return build_context_pack(file_request, repo_root=ROOT, get_repo_slug_fn=get_repo_slug)


def main() -> int:
    ap = argparse.ArgumentParser(description="CTCP local librarian (read-only context pack supplier)")
    ap.add_argument("--run-dir", default="")
    args = ap.parse_args()

    run_dir = _resolve_run_dir(args.run_dir)
    request_path = run_dir / "artifacts" / "file_request.json"
    out_path = run_dir / "artifacts" / "context_pack.json"
    failure_path = run_dir / "artifacts" / "context_pack.failure.json"
    if failure_path.exists():
        try:
            failure_path.unlink()
        except Exception:
            pass
    if not request_path.exists():
        write_failure_doc(
            run_dir,
            stage="read_request",
            error_code="request_missing",
            message=f"[ctcp_librarian] missing file_request: {request_path}",
            request_path=request_path,
            target_path=out_path,
        )
        update_librarian_context(run_dir, success=False, reason="missing file_request")
        print(f"[ctcp_librarian] missing file_request: {request_path}")
        return 1

    try:
        file_request = _read_json(request_path)
    except Exception as exc:
        write_failure_doc(
            run_dir,
            stage="read_request",
            error_code="request_invalid_json",
            message=f"[ctcp_librarian] invalid file_request json: {exc}",
            request_path=request_path,
            target_path=out_path,
        )
        update_librarian_context(run_dir, success=False, reason="invalid file_request json")
        print(f"[ctcp_librarian] invalid file_request json: {exc}")
        return 1

    try:
        context_pack = _build_context_pack(file_request)
        _write_json(out_path, context_pack)
        update_librarian_context(run_dir, success=True)
    except LibrarianContractError as exc:
        write_failure_doc(
            run_dir,
            stage=exc.stage,
            error_code=exc.error_code,
            message=str(exc),
            request_path=request_path,
            target_path=out_path,
            failed_path=exc.failed_path,
            details=exc.details,
        )
        update_librarian_context(run_dir, success=False, reason=str(exc))
        print(str(exc))
        return 1
    except Exception as exc:
        write_failure_doc(
            run_dir,
            stage="write_context_pack",
            error_code="write_failed",
            message=f"[ctcp_librarian] failed to write context_pack: {exc}",
            request_path=request_path,
            target_path=out_path,
        )
        update_librarian_context(run_dir, success=False, reason=str(exc))
        print(f"[ctcp_librarian] failed to write context_pack: {exc}")
        return 1

    print(f"[ctcp_librarian] wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
