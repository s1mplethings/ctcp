#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_core.clients import openai_compatible as _impl

DEFAULT_LOCAL_NOTES_PATH = _impl.DEFAULT_LOCAL_NOTES_PATH
ROOT = _impl.ROOT
json = _impl.json
os = _impl.os
re = _impl.re
ssl = _impl.ssl
time = _impl.time
urllib = _impl.urllib

_append_api_call = _impl._append_api_call
_call_with_retry = _impl._call_with_retry
_collect_text_from_output = _impl._collect_text_from_output
_load_local_notes_defaults = _impl._load_local_notes_defaults
_now_iso = _impl._now_iso
_post_json = _impl._post_json
_resolve_api_credentials = _impl._resolve_api_credentials
_safe_float_env = _impl._safe_float_env
_safe_int_env = _impl._safe_int_env
_sanitize_text_for_json = _impl._sanitize_text_for_json
_short_error = _impl._short_error
call_openai_responses = _impl.call_openai_responses
extract_response_text = _impl.extract_response_text
