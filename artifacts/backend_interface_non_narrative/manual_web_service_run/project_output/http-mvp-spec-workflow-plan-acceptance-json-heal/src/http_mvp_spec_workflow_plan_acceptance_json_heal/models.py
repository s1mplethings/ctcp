from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EndpointContract:
    route: str
    method: str
    description: str
    outputs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
