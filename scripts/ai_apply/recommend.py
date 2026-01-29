from __future__ import annotations
import json
from pathlib import Path
from .util import read_text

def load_rules(repo_root: Path):
    rules_path = repo_root / "ai" / "DETECTORS" / "rules.json"
    if not rules_path.exists():
        return {"version": 1, "detectors": []}
    return json.loads(rules_path.read_text(encoding="utf-8"))

def load_recipe_index(repo_root: Path):
    idx = repo_root / "ai" / "RECIPES" / "recipe_index.json"
    if not idx.exists():
        return {"version": 1, "recipes": []}
    return json.loads(idx.read_text(encoding="utf-8"))

def recommend(report_json_path: str, repo_root: str) -> list[dict]:
    report = json.loads(Path(report_json_path).read_text(encoding="utf-8"))
    profile = report.get("profile", {})
    hits = set(profile.get("text_hits", []))

    rules = load_rules(Path(repo_root))
    out = []
    for d in rules.get("detectors", []):
        match = d.get("match", {})
        any_text = match.get("any_text_in_files", [])
        if any(k in hits for k in any_text):
            out.append({
                "detector_id": d.get("id"),
                "title": d.get("title"),
                "severity": d.get("severity"),
                "suggest_recipes": d.get("suggest_recipes", [])
            })

    # score recipes
    idx = load_recipe_index(Path(repo_root))
    score = {}
    for f in out:
        for rid in f["suggest_recipes"]:
            score[rid] = score.get(rid, 0) + 1

    ranked = [{"recipe_id": k, "score": v} for k, v in sorted(score.items(), key=lambda x: (-x[1], x[0]))]
    return [{"findings": out, "ranked_recipes": ranked, "recipes": idx.get("recipes", [])}]

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("report_json")
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()
    result = recommend(args.report_json, args.repo_root)[0]
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
