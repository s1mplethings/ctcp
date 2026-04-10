#!/usr/bin/env python3
from __future__ import annotations

from llm_core.retrieval import repo_search as _impl

SEARCH_ROOTS = _impl.SEARCH_ROOTS
SKIP_DIR_NAMES = _impl.SKIP_DIR_NAMES
SKIP_SUFFIXES = _impl.SKIP_SUFFIXES
argparse = _impl.argparse
json = _impl.json
os = _impl.os
shutil = _impl.shutil
subprocess = _impl.subprocess

_build_result = _impl._build_result
_format_snippet = _impl._format_snippet
_iter_candidate_files = _impl._iter_candidate_files
_read_text_lines = _impl._read_text_lines
_rg_exclude_globs = _impl._rg_exclude_globs
_search_with_python = _impl._search_with_python
_search_with_rg = _impl._search_with_rg
_to_rel_posix = _impl._to_rel_posix
main = _impl.main
search = _impl.search
search_repo_context = _impl.search_repo_context


if __name__ == "__main__":
    raise SystemExit(main())
