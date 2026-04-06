from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PresentableEvent:
    reply_text: str
    events: list[dict[str, Any]] = field(default_factory=list)
    delivery_evidence: dict[str, Any] = field(default_factory=dict)
    developer_details: dict[str, Any] = field(default_factory=dict)
