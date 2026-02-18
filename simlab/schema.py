#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


def validate_scenario(doc: dict[str, Any], source: str) -> None:
    if not isinstance(doc, dict):
        raise ValueError(f"{source}: scenario must be an object")
    if not str(doc.get("id", "")).strip():
        raise ValueError(f"{source}: missing scenario id")
    if not str(doc.get("name", "")).strip():
        raise ValueError(f"{source}: missing scenario name")
    steps = doc.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError(f"{source}: steps must be a non-empty array")
    allowed = {"run", "write", "expect_path", "expect_text", "expect_bundle"}
    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"{source}: step#{idx} must be an object")
        keys = set(step.keys())
        if len(keys) != 1:
            raise ValueError(f"{source}: step#{idx} must contain exactly one step type")
        key = next(iter(keys))
        if key not in allowed:
            raise ValueError(f"{source}: step#{idx} has unsupported type: {key}")

