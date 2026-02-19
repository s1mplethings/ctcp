#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "workflow_registry" / "index.json"
DEFAULT_OUT = ROOT / "artifacts" / "find_result.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _tokenize(text: str) -> list[str]:
    out = []
    for part in text.lower().replace("_", "-").split():
        for p in part.split("-"):
            p = p.strip()
            if p:
                out.append(p)
    return out


def _collect_history(repo: Path) -> dict[str, int]:
    scores: dict[str, int] = {}
    roots = [
        repo / "simlab" / "_runs",
        repo / "tests" / "fixtures" / "adlc_forge_full_bundle" / "runs" / "simlab_runs",
    ]
    for base in roots:
        if not base.exists():
            continue
        for summary in base.rglob("summary.json"):
            try:
                doc = _load_json(summary)
            except Exception:
                continue
            passed = int(doc.get("passed", 0))
            failed = int(doc.get("failed", 0))
            if passed > 0 and failed == 0:
                scores["wf_minimal_patch_verify"] = scores.get("wf_minimal_patch_verify", 0) + passed
    return scores


def _score_workflow(wf: dict[str, Any], goal_tokens: list[str], history_score: int) -> tuple[int, dict[str, Any]]:
    tags = [str(x).lower() for x in wf.get("tags", [])]
    goals = [str(x).lower() for x in wf.get("supported_goals", [])]
    dep = str(wf.get("dependency_level", "med")).lower()

    tag_hits = sum(1 for t in goal_tokens if t in tags or t in goals)
    dep_bonus = {"low": 30, "med": 10, "high": 0}.get(dep, 5)
    total = tag_hits * 20 + dep_bonus + history_score * 3
    detail = {"tag_hits": tag_hits, "dependency_level": dep, "history_score": history_score, "total_score": total}
    return total, detail


def resolve(goal: str, repo: Path) -> dict[str, Any]:
    index = _load_json(INDEX_PATH)
    workflows = list(index.get("workflows", []))
    goal_tokens = _tokenize(goal)
    history = _collect_history(repo)

    ranked: list[dict[str, Any]] = []
    for wf in workflows:
        wf_id = str(wf.get("id", ""))
        score, detail = _score_workflow(wf, goal_tokens, history.get(wf_id, 0))
        ranked.append(
            {
                "id": wf_id,
                "version": str(wf.get("version", "")),
                "score": score,
                "dependency_level": str(wf.get("dependency_level", "med")),
                "path": str(wf.get("path", "")),
                "detail": detail,
            }
        )

    ranked.sort(key=lambda x: x["score"], reverse=True)
    selected = ranked[0] if ranked and ranked[0]["score"] > 0 else None
    if selected is None and workflows:
        for w in workflows:
            if str(w.get("id")) == "wf_minimal_patch_verify":
                selected = {
                    "id": str(w.get("id")),
                    "version": str(w.get("version", "")),
                    "score": 0,
                    "dependency_level": str(w.get("dependency_level", "low")),
                    "path": str(w.get("path", "")),
                    "detail": {"reason": "fallback_minimal_workflow"},
                }
                break

    result = {
        "schema_version": "ctcp-find-result-v1",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "goal": goal,
        "selected_workflow_id": selected["id"] if selected else None,
        "selected_version": selected["version"] if selected else None,
        "selected_path": selected["path"] if selected else None,
        "candidates": [
            {
                "workflow_id": r["id"],
                "version": r["version"],
                "score": r["score"],
                "why": json.dumps(r.get("detail", {}), ensure_ascii=False),
            }
            for r in ranked[:3]
        ],
        "params_schema": {
            "goal": "string",
            "constraints": "object",
            "repo_hints": "object"
        },
        "params": {"goal": goal, "constraints": {}, "repo_hints": {"headless_default": True}},
        "top_candidates": ranked[:3],
        "decision": {
            "reason": "prefer local workflow_registry + recent successful runs + low dependency",
            "history_scores": history,
            "fallback_used": bool(selected and selected.get("score", 0) == 0),
        },
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Resolve the best local workflow from workflow_registry.")
    ap.add_argument("--goal", required=True)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--repo", default=str(ROOT))
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    result = resolve(goal=args.goal, repo=repo)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[resolve_workflow] out={out.as_posix()}")
    print(f"[resolve_workflow] selected={result['selected_workflow_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
