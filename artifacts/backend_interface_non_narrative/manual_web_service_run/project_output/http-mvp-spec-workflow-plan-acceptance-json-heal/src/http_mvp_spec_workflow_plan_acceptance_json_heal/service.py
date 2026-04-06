from __future__ import annotations

from pathlib import Path

from .app import generate_payload
from .exporter import export_bundle
from .service_contract import build_contract
from .spec_builder import build_spec


def generate_project(*, goal: str, project_name: str, out_dir: Path) -> dict[str, str]:
    spec = build_spec(goal, project_name)
    contract = [row.to_dict() for row in build_contract(spec)]
    sample_response = generate_payload(goal, project_name)
    return export_bundle(spec=spec, service_contract=contract, sample_response=sample_response, out_dir=out_dir)
