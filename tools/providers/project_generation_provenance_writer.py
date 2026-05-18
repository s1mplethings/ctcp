from __future__ import annotations

import json
from typing import Any


def concrete_fast_path_provenance(*, project_type: str, reason: str, repair_attempts: int = 0) -> dict[str, Any]:
    return {
        "generation_mode": "concrete_fast_path",
        "project_type": str(project_type or "concrete_project"),
        "provider_authorship": "not_claimed",
        "local_materializer_used": True,
        "repair_attempts": int(repair_attempts),
        "reason": str(reason or "bounded concrete project fast path"),
    }


def provenance_json(provenance: dict[str, Any]) -> str:
    return json.dumps(dict(provenance), ensure_ascii=False, indent=2) + "\n"
