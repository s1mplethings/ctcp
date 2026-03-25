from __future__ import annotations

from dataclasses import dataclass

from contracts.version import PROTOCOL_VERSION


@dataclass(frozen=True)
class BackendConfig:
    protocol_version: str = PROTOCOL_VERSION
    max_auto_advance_steps: int = 1
