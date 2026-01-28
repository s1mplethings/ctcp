
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = [
    ROOT / "specs" / "contract_input" / "project_marker.schema.json",
    ROOT / "specs" / "contract_output" / "graph.schema.json",
    ROOT / "specs" / "contract_output" / "meta_pipeline_graph.schema.json",
    ROOT / "specs" / "contract_output" / "run_events.schema.json",
]

def main():
    missing = [p for p in SCHEMAS if not p.exists()]
    if missing:
        raise SystemExit(f"[contract_checks] missing schema files: {missing}")
    print("[contract_checks] schema presence ok")

    sample_meta = ROOT / "meta" / "pipeline_graph.json"
    if sample_meta.exists():
        data = json.loads(sample_meta.read_text(encoding="utf-8"))
        if "schema_version" not in data:
            raise SystemExit("[contract_checks] meta/pipeline_graph.json missing schema_version")
        print("[contract_checks] meta schema_version ok")
    else:
        print("[contract_checks] meta/pipeline_graph.json not found (ok for fresh project)")

if __name__ == "__main__":
    main()
