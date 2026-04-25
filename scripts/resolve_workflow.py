#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "workflow_registry" / "index.json"
DEFAULT_OUT = ROOT / "artifacts" / "find_result.json"
PROJECT_GENERATION_WORKFLOW_ID = "wf_project_generation_manifest"
_TASK_BINDING_HINTS = (
    "绑定任务",
    "绑定一个新任务",
    "绑定新任务",
    "新任务",
    "bind a new task",
    "bind this task",
)
_DOMAIN_LIFT_HINTS = (
    "domain lift",
    "domain-lift",
    "域提升",
    "完整产品域",
    "coverage gate",
    "user_acceptance_status",
    "internal_runtime_status",
)
_RERUN_HINTS = (
    "重跑生成测试",
    "重跑测试",
    "重新生成",
    "rerun generation test",
    "rerun the generation test",
    "rerun",
)
_ROUGH_GOAL_PRODUCT_HINTS = (
    "粗目标",
    "不要细规格",
    "自己做产品定义并生成",
    "rough goal",
    "product definition",
    "project generation",
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _tokenize(text: str) -> list[str]:
    out: list[str] = []
    for token in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{1,12}", text.lower()):
        norm = token.strip().replace("_", "-")
        if not norm:
            continue
        if "-" in norm:
            out.extend([x for x in norm.split("-") if x])
        else:
            out.append(norm)
    return out


def _is_project_generation_goal(goal: str) -> bool:
    text = str(goal or "").strip()
    if not text:
        return False
    lower = text.lower()
    task_binding = any(key in text or key in lower for key in _TASK_BINDING_HINTS)
    domain_lift = any(key in text or key in lower for key in _DOMAIN_LIFT_HINTS)
    rerun_signal = any(key in text or key in lower for key in _RERUN_HINTS)
    rough_goal_signal = any(key in text or key in lower for key in _ROUGH_GOAL_PRODUCT_HINTS)
    has_generate_signal = any(
        key in lower
        for key in (
            "generate",
            "生成",
            "产出",
            "输出",
            "scaffold",
            "build a project",
            "project generation",
            "generation test",
            "generation repair",
        )
    )
    has_build_signal = any(
        key in lower
        for key in (
            "build",
            "create",
            "make",
            "做一个",
            "做个",
            "搭一个",
            "实现一个",
            "写一个",
        )
    )
    has_project_signal = any(
        key in lower
        for key in (
            "project",
            "repo",
            "repository",
            "app",
            "application",
            "platform",
            "workspace",
            "dashboard",
            "portal",
            "task management",
            "task collaboration",
            "team task",
            "plane-lite",
            "focalboard-lite",
            "项目",
            "工程",
            "应用",
            "平台",
            "工作台",
            "管理平台",
            "协作平台",
            "任务协作",
            "团队任务",
            "任务管理",
            "看板",
            "结构化",
            "交付",
            "workflow",
            "asset library",
            "bug tracker",
            "build / release",
            "docs center",
            "独立游戏",
            "素材",
            "bug",
            "构建",
            "发布",
            "文档中心",
        )
    )
    has_runnable_delivery_signal = any(
        key in lower
        for key in (
            "可运行",
            "本地可运行",
            "双击",
            "zip",
            "交付",
            "单文件",
            "html",
            "页面",
            "网站",
            "web app",
            "landing page",
            "index.html",
            "local-first",
            "local first",
            "本地部署",
            "本地优先",
        )
    )
    if (task_binding and (domain_lift or rerun_signal) and (has_project_signal or rough_goal_signal or has_generate_signal)):
        return True
    return bool((has_generate_signal or has_build_signal or rough_goal_signal) and (has_project_signal or has_runnable_delivery_signal or domain_lift or rerun_signal))


def _collect_history(repo: Path, fallback_workflow_id: str) -> dict[str, int]:
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
                scores[fallback_workflow_id] = scores.get(fallback_workflow_id, 0) + passed
    return scores


def _score_workflow(
    wf: dict[str, Any],
    goal_tokens: list[str],
    history_score: int,
    *,
    project_generation_goal: bool,
) -> tuple[int, dict[str, Any]]:
    tags = [str(x).lower() for x in wf.get("tags", [])]
    goals = [str(x).lower() for x in wf.get("supported_goals", [])]
    dep = str(wf.get("dependency_level", "med")).lower()
    wf_id = str(wf.get("id", "")).strip()

    tag_hits = sum(1 for t in goal_tokens if t in tags or t in goals)
    dep_bonus = {"low": 30, "med": 10, "high": 0}.get(dep, 5)
    project_bias = 0
    if project_generation_goal:
        if (
            "project-generation" in tags
            or "project-generation" in goals
            or wf_id == PROJECT_GENERATION_WORKFLOW_ID
        ):
            project_bias = 220
        elif "patch" in tags or "bugfix" in goals:
            project_bias = -40
    total = tag_hits * 20 + dep_bonus + history_score * 3 + project_bias
    detail = {
        "tag_hits": tag_hits,
        "dependency_level": dep,
        "history_score": history_score,
        "project_bias": project_bias,
        "total_score": total,
    }
    return total, detail


def resolve(goal: str, repo: Path) -> dict[str, Any]:
    index = _load_json(INDEX_PATH)
    fallback_id = str(index.get("resolver_policy", {}).get("fallback_workflow_id", "")).strip() or "wf_orchestrator_only"
    workflows = list(index.get("workflows", []))
    goal_tokens = _tokenize(goal)
    project_generation_goal = _is_project_generation_goal(goal)
    history = _collect_history(repo, fallback_id)

    ranked: list[dict[str, Any]] = []
    for wf in workflows:
        wf_id = str(wf.get("id", ""))
        score, detail = _score_workflow(
            wf,
            goal_tokens,
            history.get(wf_id, 0),
            project_generation_goal=project_generation_goal,
        )
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
            if str(w.get("id")) == fallback_id:
                selected = {
                    "id": str(w.get("id")),
                    "version": str(w.get("version", "")),
                    "score": 0,
                    "dependency_level": str(w.get("dependency_level", "low")),
                    "path": str(w.get("path", "")),
                    "detail": {"reason": "fallback_workflow"},
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
            "project_generation_goal": project_generation_goal,
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
