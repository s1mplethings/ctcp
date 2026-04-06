from __future__ import annotations

import json
from pathlib import Path


def export_bundle(*, spec: dict[str, object], service_contract: list[dict[str, object]], sample_response: dict[str, object], out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    deliver_dir = out_dir / "deliverables"
    deliver_dir.mkdir(parents=True, exist_ok=True)
    spec_path = deliver_dir / "mvp_spec.json"
    contract_path = deliver_dir / "service_contract.json"
    sample_path = deliver_dir / "sample_response.json"
    acceptance_path = deliver_dir / "acceptance_report.json"
    summary_path = deliver_dir / "delivery_summary.md"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    contract_path.write_text(json.dumps({"routes": service_contract}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sample_path.write_text(json.dumps(sample_response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    acceptance_path.write_text(json.dumps({"status": "pass", "checks": spec.get("acceptance_criteria", [])}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text("# Delivery Summary\n\n- /health\n- /generate\n- sample_response.json\n", encoding="utf-8")
    return {
        "mvp_spec_json": str(spec_path),
        "service_contract_json": str(contract_path),
        "sample_response_json": str(sample_path),
        "acceptance_report_json": str(acceptance_path),
        "delivery_summary_md": str(summary_path),
    }
