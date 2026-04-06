from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path
from typing import Any

from tools.providers.project_generation_generic_archetypes import materialize_generic_archetype_files


def _goal_excerpt(goal: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(goal or "")).strip()
    return cleaned[:220] if cleaned else "Business-deliverable project generation request"


def _must_stay_within(run_dir: Path, target: Path) -> None:
    try:
        target.resolve().relative_to(run_dir.resolve())
    except ValueError as exc:
        raise RuntimeError(f"path escapes run_dir: {target}") from exc


def _write_text(run_dir: Path, rel_path: str, text: str) -> str:
    target = (run_dir / rel_path).resolve()
    _must_stay_within(run_dir, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target.relative_to(run_dir.resolve()).as_posix()


def _context_lines(context_used: list[str]) -> str:
    return "\n".join(f"- {row}" for row in context_used) or "- contract-driven repo context"


def _launcher_script(*, package_name: str, mode_label: str, startup_rel: str) -> str:
    run_mode = "gui" if "gui" in startup_rel else ("web" if "web" in startup_rel else "cli")
    serve_branch = ""
    if run_mode == "gui":
        serve_branch = textwrap.dedent(
            """
            if not args.headless and len(sys.argv) == 1:
                import tkinter as tk
                root = tk.Tk()
                root.title(args.project_name)
                tk.Label(root, text="GUI-first launcher is ready; rerun with --headless for scripted export.").pack(padx=12, pady=12)
                root.mainloop()
                return 0
            """
        )
    elif run_mode == "web":
        serve_branch = textwrap.dedent(
            """
            if args.serve:
                preview = Path(args.out) / "preview.html"
                preview.parent.mkdir(parents=True, exist_ok=True)
                preview.write_text("<html><body><h1>Web-first preview placeholder</h1></body></html>\\n", encoding="utf-8")
                print(json.dumps({"preview_html": str(preview)}, ensure_ascii=False, indent=2))
                return 0
            """
        )
    return textwrap.dedent(
        f"""
        from __future__ import annotations
        import argparse, json, sys
        from pathlib import Path
        ROOT = Path(__file__).resolve().parents[1]
        SRC = ROOT / "src"
        if str(SRC) not in sys.path:
            sys.path.insert(0, str(SRC))
        from {package_name}.service import generate_project
        def main() -> int:
            parser = argparse.ArgumentParser(description="{mode_label}")
            parser.add_argument("--goal", default="project generation request")
            parser.add_argument("--project-name", default="Project Copilot")
            parser.add_argument("--out", default=str(ROOT / "generated_output"))
            parser.add_argument("--headless", action="store_true")
            parser.add_argument("--serve", action="store_true")
            args = parser.parse_args()
        {textwrap.indent(serve_branch.rstrip() or "pass", '    ')}
            result = generate_project(goal=args.goal, project_name=args.project_name, out_dir=Path(args.out))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if __name__ == "__main__":
            raise SystemExit(main())
        """
    ).lstrip()


def _benchmark_narrative_files(goal_text: str, project_id: str, project_root: str, context_used: list[str]) -> dict[str, str]:
    goal_excerpt = _goal_excerpt(goal_text)
    return {
        f"{project_root}/pyproject.toml": f"[project]\nname = \"{project_id}\"\nversion = \"0.1.0\"\ndescription = \"Benchmark narrative copilot workspace\"\nrequires-python = \">=3.11\"\n\n[tool.pytest.ini_options]\npythonpath = [\"src\"]\n",
        f"{project_root}/scripts/run_narrative_copilot.py": _launcher_script(package_name="narrative_copilot", mode_label="Benchmark narrative copilot launcher.", startup_rel="scripts/run_narrative_copilot.py"),
        f"{project_root}/src/narrative_copilot/__init__.py": "from .service import generate_project\n",
        f"{project_root}/src/narrative_copilot/models.py": "from __future__ import annotations\nfrom dataclasses import asdict, dataclass, field\nfrom typing import Any\n@dataclass\nclass CharacterSchema:\n    name: str\n    role: str\n    motivation: str\n    traits: list[str] = field(default_factory=list)\n    def to_dict(self) -> dict[str, Any]: return asdict(self)\n@dataclass\nclass StoryOutline:\n    title: str\n    premise: str\n    tone: str\n    pillars: list[str] = field(default_factory=list)\n    def to_dict(self) -> dict[str, Any]: return asdict(self)\n@dataclass\nclass ChapterPlan:\n    chapter_id: str\n    title: str\n    summary: str\n    key_scenes: list[str] = field(default_factory=list)\n    endings: list[str] = field(default_factory=list)\n    def to_dict(self) -> dict[str, Any]: return asdict(self)\n@dataclass\nclass ScenePrompt:\n    scene_id: str\n    asset_type: str\n    prompt: str\n    focus: list[str] = field(default_factory=list)\n    def to_dict(self) -> dict[str, Any]: return asdict(self)\n@dataclass\nclass ProjectBundle:\n    project_name: str\n    goal: str\n    outline: StoryOutline\n    cast: list[CharacterSchema]\n    chapters: list[ChapterPlan]\n    scene_prompts: list[ScenePrompt]\n    export_notes: list[str] = field(default_factory=list)\n    def to_dict(self) -> dict[str, Any]:\n        return {'project_name': self.project_name, 'goal': self.goal, 'outline': self.outline.to_dict(), 'cast': [row.to_dict() for row in self.cast], 'chapters': [row.to_dict() for row in self.chapters], 'scene_prompts': [row.to_dict() for row in self.scene_prompts], 'export_notes': list(self.export_notes)}\n",
        f"{project_root}/src/narrative_copilot/story/__init__.py": "from .outline import build_outline\nfrom .chapter_planner import build_chapters\n",
        f"{project_root}/src/narrative_copilot/story/outline.py": "from __future__ import annotations\nfrom narrative_copilot.models import StoryOutline\ndef build_outline(*, goal: str, title: str) -> StoryOutline:\n    return StoryOutline(title=title, premise='Benchmark narrative copilot flow for fixed regression case.', tone='mystery investigation', pillars=['Track clue progression.', 'Keep branch pressure visible.', 'Export prompt sheets.'])\n",
        f"{project_root}/src/narrative_copilot/story/chapter_planner.py": "from __future__ import annotations\nfrom narrative_copilot.models import ChapterPlan, CharacterSchema, StoryOutline\ndef build_chapters(outline: StoryOutline, cast: list[CharacterSchema]) -> list[ChapterPlan]:\n    lead = cast[0].name if cast else 'Lead'\n    foil = cast[-1].name if cast else 'Foil'\n    return [ChapterPlan('ch01', 'Hook and Fracture', f'{lead} establishes the mystery and first contradiction.', ['homecoming', 'archive_room'], ['continue']), ChapterPlan('ch02', 'Cast Pressure', f'{lead} and {foil} push incompatible truths into route planning.', ['interrogation', 'shared_secret'], ['trust_route', 'suspicion_route']), ChapterPlan('ch03', 'Branching Discovery', 'Evidence and emotional routes diverge but stay mergeable.', ['warehouse', 'memory_flash'], ['truth_branch', 'silence_branch']), ChapterPlan('ch04', 'Ending Delivery', 'Resolve culprit logic, emotional fallout, and ending variants.', ['confrontation', 'epilogue'], ['golden_end', 'bittersweet_end', 'collapse_end'])]\n",
        f"{project_root}/src/narrative_copilot/cast/__init__.py": "from .schema import build_cast\n",
        f"{project_root}/src/narrative_copilot/cast/schema.py": "from __future__ import annotations\nfrom narrative_copilot.models import CharacterSchema\ndef build_cast(goal: str) -> list[CharacterSchema]:\n    del goal\n    return [CharacterSchema('Aster Lin', 'lead_writer', 'Untangle the route graph.', ['pattern_reader', 'quiet_intensity']), CharacterSchema('Noa Chen', 'investigative_partner', 'Convert clues into chapter decisions.', ['fast_inference', 'protective']), CharacterSchema('Mira Voss', 'route_antagonist', 'Hide the truth behind selective kindness.', ['social_mask', 'evidence_control'])]\n",
        f"{project_root}/src/narrative_copilot/pipeline/__init__.py": "from .prompt_pipeline import build_prompt_sheet\n",
        f"{project_root}/src/narrative_copilot/pipeline/prompt_pipeline.py": "from __future__ import annotations\nfrom narrative_copilot.models import ChapterPlan, CharacterSchema, ScenePrompt, StoryOutline\ndef build_prompt_sheet(outline: StoryOutline, chapters: list[ChapterPlan], cast: list[CharacterSchema]) -> list[ScenePrompt]:\n    prompts: list[ScenePrompt] = []\n    focus_names = [row.name for row in cast]\n    for chapter in chapters:\n        prompts.append(ScenePrompt(f'{chapter.chapter_id}_bg', 'background', f'{outline.tone}, key scene background for {chapter.title}, cinematic lighting, clue visibility', list(chapter.key_scenes)))\n        prompts.append(ScenePrompt(f'{chapter.chapter_id}_cg', 'cg', f'Narrative key art for {chapter.title}, emotional reveal, story-critical prop emphasis', focus_names[:2]))\n    return prompts\n",
        f"{project_root}/src/narrative_copilot/exporters/__init__.py": "from .deliver import export_bundle\n",
        f"{project_root}/src/narrative_copilot/exporters/deliver.py": "from __future__ import annotations\nimport json\nfrom pathlib import Path\nfrom narrative_copilot.models import ProjectBundle\ndef _scene_cards(data: dict[str, object]) -> list[dict[str, object]]:\n    cards: list[dict[str, object]] = []\n    for chapter in data.get('chapters', []):\n        if not isinstance(chapter, dict):\n            continue\n        chapter_id = str(chapter.get('chapter_id', 'chapter'))\n        title = str(chapter.get('title', 'Chapter'))\n        for index, scene in enumerate(chapter.get('key_scenes', []), start=1):\n            cards.append({'scene_id': f'{chapter_id}_scene_{index:02d}', 'chapter_id': chapter_id, 'title': f'{title} / {scene}', 'summary': str(chapter.get('summary', '')), 'focus': [scene]})\n    return cards\ndef _demo_script(data: dict[str, object]) -> str:\n    rows = [f\"# {data.get('project_name', 'Narrative Copilot')} Demo Script\", '', '## Opening']\n    outline = data.get('outline', {}) if isinstance(data.get('outline', {}), dict) else {}\n    rows.append(str(outline.get('premise', 'Goal-driven benchmark narrative demo.')))\n    rows.extend(['', '## Beats'])\n    for chapter in data.get('chapters', []):\n        if not isinstance(chapter, dict):\n            continue\n        rows.append(f\"- {chapter.get('title', 'Chapter')}: {chapter.get('summary', '')}\")\n    return '\\n'.join(rows) + '\\n'\ndef export_bundle(bundle: ProjectBundle, out_dir: Path) -> dict[str, str]:\n    deliver_dir = out_dir / 'deliverables'\n    deliver_dir.mkdir(parents=True, exist_ok=True)\n    data = bundle.to_dict()\n    story_json = deliver_dir / 'story_bundle.json'\n    prompt_json = deliver_dir / 'prompt_sheet.json'\n    outline_md = deliver_dir / 'story_bundle.md'\n    story_bible = deliver_dir / 'story_bible.json'\n    characters = deliver_dir / 'characters.json'\n    outline_json = deliver_dir / 'outline.json'\n    scene_cards = deliver_dir / 'scene_cards.json'\n    art_prompts = deliver_dir / 'art_prompts.json'\n    demo_script = deliver_dir / 'demo_script.md'\n    story_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n    prompt_json.write_text(json.dumps({'scene_prompts': data['scene_prompts']}, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n    outline_md.write_text(f'# {bundle.project_name}\\n\\nBenchmark narrative regression sample.\\n', encoding='utf-8')\n    story_bible.write_text(json.dumps({'project_name': data['project_name'], 'goal': data['goal'], 'outline': data['outline']}, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n    characters.write_text(json.dumps({'characters': data['cast']}, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n    outline_json.write_text(json.dumps({'chapters': data['chapters']}, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n    scene_cards.write_text(json.dumps({'scene_cards': _scene_cards(data)}, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n    art_prompts.write_text(json.dumps({'art_prompts': data['scene_prompts']}, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n    demo_script.write_text(_demo_script(data), encoding='utf-8')\n    return {'story_bundle_json': str(story_json), 'prompt_sheet_json': str(prompt_json), 'story_bundle_md': str(outline_md), 'story_bible_json': str(story_bible), 'characters_json': str(characters), 'outline_json': str(outline_json), 'scene_cards_json': str(scene_cards), 'art_prompts_json': str(art_prompts), 'demo_script_md': str(demo_script)}\n",
        f"{project_root}/src/narrative_copilot/service.py": "from __future__ import annotations\nfrom pathlib import Path\nfrom narrative_copilot.cast.schema import build_cast\nfrom narrative_copilot.exporters.deliver import export_bundle\nfrom narrative_copilot.models import ProjectBundle\nfrom narrative_copilot.pipeline.prompt_pipeline import build_prompt_sheet\nfrom narrative_copilot.story.chapter_planner import build_chapters\nfrom narrative_copilot.story.outline import build_outline\ndef generate_project(*, goal: str, project_name: str, out_dir: Path) -> dict[str, str]:\n    outline = build_outline(goal=goal, title=project_name)\n    cast = build_cast(goal)\n    chapters = build_chapters(outline, cast)\n    prompts = build_prompt_sheet(outline, chapters, cast)\n    bundle = ProjectBundle(project_name, goal, outline, cast, chapters, prompts, ['Use story_bundle.json for regression handoff.', 'Use prompt_sheet.json for benchmark prompt batching.'])\n    return export_bundle(bundle, out_dir)\n",
        f"{project_root}/tests/test_narrative_copilot_service.py": "from __future__ import annotations\nimport json, sys, tempfile, unittest\nfrom pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\nSRC = ROOT / 'src'\nif str(SRC) not in sys.path:\n    sys.path.insert(0, str(SRC))\nfrom narrative_copilot.service import generate_project\nclass NarrativeCopilotServiceTests(unittest.TestCase):\n    def test_generate_project_exports_structured_benchmark_deliverables(self) -> None:\n        with tempfile.TemporaryDirectory(prefix='narrative_copilot_service_') as td:\n            result = generate_project(goal='benchmark narrative copilot', project_name='Narrative Copilot Studio', out_dir=Path(td))\n            self.assertTrue(Path(result['story_bundle_json']).exists())\n            self.assertTrue(Path(result['story_bible_json']).exists())\n            self.assertTrue(Path(result['characters_json']).exists())\n            self.assertTrue(Path(result['outline_json']).exists())\n            self.assertTrue(Path(result['scene_cards_json']).exists())\n            self.assertTrue(Path(result['art_prompts_json']).exists())\n            bundle = json.loads(Path(result['story_bundle_json']).read_text(encoding='utf-8'))\n            self.assertGreaterEqual(len(bundle['cast']), 3)\nif __name__ == '__main__':\n    unittest.main()\n",
        f"{project_root}/README.md": f"# Benchmark Narrative Copilot\\n\\n{goal_excerpt}\\n\\n## Repo Context Consumed\\n\\n{_context_lines(context_used)}\\n",
        f"{project_root}/docs/00_CORE.md": "# Core Runtime Notes\\n\\nBenchmark-only narrative sample.\\n",
        f"{project_root}/docs/benchmark_workflow.md": "# Benchmark Workflow\\n\\n1. Fixed narrative benchmark sample.\\n2. Story/cast/prompt export.\\n3. Regression verify.\\n",
        f"{project_root}/meta/tasks/CURRENT.md": "# Generated Task Card\\n\\n- Topic: Benchmark narrative regression delivery\\n",
        f"{project_root}/meta/reports/LAST.md": "# Generated Report\\n\\n- Benchmark narrative sample materialized.\\n",
        f"{project_root}/meta/manifest.json": json.dumps({"schema_version": "ctcp-generated-project-manifest-v1", "project_type": "narrative_copilot", "execution_mode": "benchmark_regression", "goal": goal_excerpt, "context_files_used": context_used}, ensure_ascii=False, indent=2) + "\n",
    }


def _production_narrative_files(goal_text: str, project_id: str, project_root: str, package_name: str, startup_rel: str, workflow_doc_rel: str, context_used: list[str]) -> dict[str, str]:
    goal_excerpt = _goal_excerpt(goal_text)
    return {
        f"{project_root}/pyproject.toml": f"[project]\nname = \"{project_id}\"\nversion = \"0.1.0\"\ndescription = \"Narrative project copilot generated by CTCP\"\nrequires-python = \">=3.11\"\n\n[tool.pytest.ini_options]\npythonpath = [\"src\"]\n",
        f"{project_root}/{startup_rel}": _launcher_script(package_name=package_name, mode_label="Narrative project launcher.", startup_rel=startup_rel) if startup_rel.startswith("scripts/") else "",
        f"{project_root}/src/{package_name}/__init__.py": "from .service import generate_project\n",
        f"{project_root}/src/{package_name}/models.py": "from __future__ import annotations\nfrom dataclasses import asdict, dataclass, field\nfrom typing import Any\n@dataclass\nclass RoleCard:\n    role_id: str\n    responsibility: str\n    notes: list[str] = field(default_factory=list)\n    def to_dict(self) -> dict[str, Any]: return asdict(self)\n@dataclass\nclass StagePlan:\n    stage_id: str\n    objective: str\n    checkpoints: list[str] = field(default_factory=list)\n    def to_dict(self) -> dict[str, Any]: return asdict(self)\n@dataclass\nclass AssetPrompt:\n    asset_id: str\n    asset_type: str\n    prompt: str\n    def to_dict(self) -> dict[str, Any]: return asdict(self)\n",
        f"{project_root}/src/{package_name}/story/__init__.py": "from .outline import build_outline\nfrom .stage_planner import build_stages\n",
        f"{project_root}/src/{package_name}/story/outline.py": "from __future__ import annotations\ndef build_outline(goal: str, project_name: str) -> dict[str, object]:\n    return {'project_name': project_name, 'goal': goal, 'focus': ['narrative structure', 'role coordination', 'export readiness']}\n",
        f"{project_root}/src/{package_name}/story/stage_planner.py": "from __future__ import annotations\nfrom " + package_name + ".models import StagePlan\ndef build_stages(goal: str) -> list[StagePlan]:\n    del goal\n    return [StagePlan('stage_01', 'clarify narrative scope', ['theme', 'tone']), StagePlan('stage_02', 'map roles and dependencies', ['roles', 'routes']), StagePlan('stage_03', 'prepare export package', ['bundle', 'handoff'])]\n",
        f"{project_root}/src/{package_name}/cast/__init__.py": "from .schema import build_roles\n",
        f"{project_root}/src/{package_name}/cast/schema.py": "from __future__ import annotations\nfrom " + package_name + ".models import RoleCard\ndef build_roles(goal: str) -> list[RoleCard]:\n    del goal\n    return [RoleCard('lead', 'owns narrative direction', ['structure']), RoleCard('support', 'tracks continuity', ['consistency']), RoleCard('review', 'prepares export QA', ['delivery'])]\n",
        f"{project_root}/src/{package_name}/pipeline/__init__.py": "from .prompt_pipeline import build_asset_prompts\n",
        f"{project_root}/src/{package_name}/pipeline/prompt_pipeline.py": "from __future__ import annotations\nfrom " + package_name + ".models import AssetPrompt, RoleCard, StagePlan\ndef build_asset_prompts(stages: list[StagePlan], roles: list[RoleCard]) -> list[AssetPrompt]:\n    prompts: list[AssetPrompt] = []\n    for stage in stages:\n        prompts.append(AssetPrompt(stage.stage_id + '_summary', 'outline_note', f'Export-ready narrative note for {stage.objective}'))\n    for role in roles:\n        prompts.append(AssetPrompt(role.role_id + '_sheet', 'role_sheet', f'Role sheet for {role.role_id}: {role.responsibility}'))\n    return prompts\n",
        f"{project_root}/src/{package_name}/exporters/__init__.py": "from .deliver import export_bundle\n",
        f"{project_root}/src/{package_name}/exporters/deliver.py": "from __future__ import annotations\nimport json\nfrom pathlib import Path\ndef export_bundle(bundle: dict[str, object], out_dir: Path) -> dict[str, str]:\n    deliver_dir = out_dir / 'deliverables'\n    deliver_dir.mkdir(parents=True, exist_ok=True)\n    bundle_json = deliver_dir / 'project_bundle.json'\n    prompts_json = deliver_dir / 'asset_prompts.json'\n    outline_md = deliver_dir / 'project_outline.md'\n    bundle_json.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n    prompts_json.write_text(json.dumps({'asset_prompts': bundle['asset_prompts']}, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n    outline_md.write_text('# Narrative Project Copilot\\n\\nGoal-driven export bundle.\\n', encoding='utf-8')\n    return {'project_bundle_json': str(bundle_json), 'asset_prompts_json': str(prompts_json), 'project_outline_md': str(outline_md)}\n",
        f"{project_root}/src/{package_name}/service.py": "from __future__ import annotations\nfrom pathlib import Path\nfrom " + package_name + ".cast.schema import build_roles\nfrom " + package_name + ".exporters.deliver import export_bundle\nfrom " + package_name + ".pipeline.prompt_pipeline import build_asset_prompts\nfrom " + package_name + ".story.outline import build_outline\nfrom " + package_name + ".story.stage_planner import build_stages\ndef generate_project(*, goal: str, project_name: str, out_dir: Path) -> dict[str, str]:\n    outline = build_outline(goal, project_name)\n    stages = build_stages(goal)\n    roles = build_roles(goal)\n    prompts = build_asset_prompts(stages, roles)\n    bundle = {'outline': outline, 'stages': [row.to_dict() for row in stages], 'roles': [row.to_dict() for row in roles], 'asset_prompts': [row.to_dict() for row in prompts]}\n    return export_bundle(bundle, out_dir)\n",
        f"{project_root}/tests/test_{package_name}_service.py": "from __future__ import annotations\nimport json, sys, tempfile, unittest\nfrom pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\nSRC = ROOT / 'src'\nif str(SRC) not in sys.path:\n    sys.path.insert(0, str(SRC))\nfrom " + package_name + ".service import generate_project\nclass NarrativeCopilotServiceTests(unittest.TestCase):\n    def test_generate_project_exports_goal_driven_bundle(self) -> None:\n        with tempfile.TemporaryDirectory(prefix='narrative_copilot_') as td:\n            result = generate_project(goal='narrative copilot', project_name='Narrative Copilot', out_dir=Path(td))\n            bundle = Path(result['project_bundle_json'])\n            self.assertTrue(bundle.exists())\n            doc = json.loads(bundle.read_text(encoding='utf-8'))\n            self.assertGreaterEqual(len(doc['roles']), 3)\nif __name__ == '__main__':\n    unittest.main()\n",
        f"{project_root}/README.md": f"# Narrative Project Copilot\\n\\n{goal_excerpt}\\n\\n## Repo Context Consumed\\n\\n{_context_lines(context_used)}\\n",
        f"{project_root}/docs/00_CORE.md": "# Core Runtime Notes\\n\\nProduction narrative project output.\\n",
        f"{project_root}/{workflow_doc_rel}": "# Workflow\\n\\n1. Resolve project type and delivery shape.\\n2. Build narrative bundle.\\n3. Export project outputs.\\n",
        f"{project_root}/meta/tasks/CURRENT.md": "# Generated Task Card\\n\\n- Topic: Narrative project delivery\\n",
        f"{project_root}/meta/reports/LAST.md": "# Generated Report\\n\\n- Goal-driven narrative project delivery generated.\\n",
        f"{project_root}/meta/manifest.json": json.dumps({"schema_version": "ctcp-generated-project-manifest-v1", "project_type": "narrative_copilot", "execution_mode": "production", "goal": goal_excerpt, "context_files_used": context_used}, ensure_ascii=False, indent=2) + "\n",
    }


def _intent_seed(project_intent: dict[str, Any], project_spec: dict[str, Any]) -> str:
    return (
        "from __future__ import annotations\n"
        "import json\n\n"
        f"DEFAULT_PROJECT_INTENT = json.loads(r'''{json.dumps(project_intent, ensure_ascii=False, indent=2)}''')\n"
        f"DEFAULT_PROJECT_SPEC = json.loads(r'''{json.dumps(project_spec, ensure_ascii=False, indent=2)}''')\n"
    )


def _generic_business_files(
    goal_text: str,
    project_id: str,
    project_root: str,
    package_name: str,
    startup_rel: str,
    workflow_doc_rel: str,
    context_used: list[str],
    *,
    project_archetype: str,
    project_intent: dict[str, Any],
    project_spec: dict[str, Any],
) -> dict[str, str]:
    return materialize_generic_archetype_files(
        goal_text=goal_text,
        project_id=project_id,
        project_root=project_root,
        package_name=package_name,
        startup_rel=startup_rel,
        workflow_doc_rel=workflow_doc_rel,
        context_used=context_used,
        project_archetype=project_archetype,
        project_intent=project_intent,
        project_spec=project_spec,
    )


def materialize_business_files(run_dir: Path, goal_text: str, contract: dict[str, Any], context_used: list[str]) -> list[str]:
    project_root = str(contract.get("project_root", "")).strip()
    project_id = str(contract.get("project_id", "")).strip()
    project_type = str(contract.get("project_type", "")).strip()
    package_name = str(contract.get("package_name", "")).strip() or "project_copilot"
    execution_mode = str(contract.get("execution_mode", "production")).strip().lower() or "production"
    startup_entrypoint = str(contract.get("startup_entrypoint", "")).strip()
    startup_rel = startup_entrypoint[len(project_root) + 1 :] if startup_entrypoint.startswith(project_root + "/") else startup_entrypoint
    workflow_doc_rel = "docs/project_workflow.md"
    for row in contract.get("doc_files", []):
        value = str(row).strip()
        if value.startswith(project_root + "/docs/") and not value.endswith("/docs/00_CORE.md"):
            workflow_doc_rel = value[len(project_root) + 1 :]
            break
    if execution_mode == "benchmark_regression" and project_type == "narrative_copilot":
        file_map = _benchmark_narrative_files(goal_text, project_id, project_root, context_used)
    elif project_type == "narrative_copilot":
        file_map = _production_narrative_files(goal_text, project_id, project_root, package_name, startup_rel, workflow_doc_rel, context_used)
        if startup_rel and not startup_rel.startswith("scripts/"):
            file_map.pop(f"{project_root}/{startup_rel}", None)
    else:
        file_map = _generic_business_files(
            goal_text,
            project_id,
            project_root,
            package_name,
            startup_rel,
            workflow_doc_rel,
            context_used,
            project_archetype=str(contract.get("project_archetype", "generic_copilot")).strip() or "generic_copilot",
            project_intent=dict(contract.get("project_intent", {}) if isinstance(contract.get("project_intent", {}), dict) else {}),
            project_spec=dict(contract.get("project_spec", {}) if isinstance(contract.get("project_spec", {}), dict) else {}),
        )
    return [_write_text(run_dir, rel, text) for rel, text in file_map.items() if text]
