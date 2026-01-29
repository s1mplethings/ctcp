from __future__ import annotations
import json
import shutil
from pathlib import Path
from .scan_repo import scan_repo
from .util import write_json

def _load_recipe(repo_root: Path, recipe_id: str) -> dict:
    idx = json.loads((repo_root / "ai" / "RECIPES" / "recipe_index.json").read_text(encoding="utf-8"))
    rec = next((r for r in idx.get("recipes", []) if r["id"] == recipe_id), None)
    if not rec:
        raise SystemExit(f"recipe not found: {recipe_id}")
    recipe_dir = repo_root / rec["path"]
    recipe_json = recipe_dir / "recipe.json"
    if not recipe_json.exists():
        raise SystemExit(f"recipe.json missing: {recipe_json}")
    data = json.loads(recipe_json.read_text(encoding="utf-8"))
    data["_dir"] = str(recipe_dir)
    return data

def build_bundle(repo_root: str, target_repo: str, recipe_id: str, out_dir: str):
    repo_root_p = Path(repo_root).resolve()
    target_p = Path(target_repo).resolve()
    out = Path(out_dir).resolve()
    (out / "patches").mkdir(parents=True, exist_ok=True)

    profile = scan_repo(str(target_p))
    report = {"scanned_at": profile.get("scanned_at",""), "profile": profile, "findings": []}
    write_json(out / "report.json", report)
    (out / "report.md").write_text(
        f"# Scan Report\n\n- target: {profile['target']}\n\n"
        f"## Profile\n- build_system: {profile['build_system']}\n- has_qt: {profile['has_qt']}\n"
        f"- has_qt_webengine: {profile['has_qt_webengine']}\n- web_roots: {profile['web_roots']}\n",
        encoding="utf-8"
    )

    recipe = _load_recipe(repo_root_p, recipe_id)
    tokens = {k: v.get("default","") for k, v in recipe.get("tokens", {}).items()}
    # auto-fill WEB_ROOT if possible
    if "WEB_ROOT" in tokens and profile.get("web_roots"):
        tokens["WEB_ROOT"] = profile["web_roots"][0]

    write_json(out / "tokens.json", tokens)

    # copy patch files
    copied = []
    for p in recipe.get("patches", []):
        src = Path(recipe["_dir"]) / p["path"]
        if src.exists():
            dst = out / "patches" / Path(p["path"]).name
            shutil.copyfile(src, dst)
            copied.append(str(dst.name))
    changes = "\n".join(f"- patch: {c}" for c in copied) if copied else "- (no patches copied)"
    (out / "plan.md").write_text(
        f"# Migration Plan\n\n- target: {target_p}\n- recipe: {recipe_id}\n\n"
        f"## Intended changes\n{changes}\n\n"
        f"## Tokens\n```json\n{json.dumps(tokens, ensure_ascii=False, indent=2)}\n```\n\n"
        f"## Apply\n```bash\ngit apply patches/*.patch\n```\n",
        encoding="utf-8"
    )
    (out / "verify.md").write_text("\n".join(recipe.get("verify", {}).get("commands", [])) + "\n", encoding="utf-8")
    (out / "rollback.md").write_text("git apply -R patches/*.patch\n", encoding="utf-8")
    return out

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("target_repo")
    ap.add_argument("--recipe", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()
    out = build_bundle(args.repo_root, args.target_repo, args.recipe, args.out)
    print(str(out))

if __name__ == "__main__":
    main()
