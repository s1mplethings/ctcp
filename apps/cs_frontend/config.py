from __future__ import annotations

from dataclasses import dataclass

from contracts.version import PROTOCOL_VERSION


@dataclass(frozen=True)
class FrontendConfig:
    protocol_version: str = PROTOCOL_VERSION
    default_language: str = "zh"
