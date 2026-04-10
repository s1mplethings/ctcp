from __future__ import annotations

from llm_core.dispatch import result as _impl

Path = _impl.Path

_is_within = _impl._is_within
apply_dispatch_evidence = _impl.apply_dispatch_evidence
normalize_dispatch_result = _impl.normalize_dispatch_result
normalize_executed_target_result = _impl.normalize_executed_target_result
provider_mode = _impl.provider_mode
