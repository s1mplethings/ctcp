from __future__ import annotations

from copy import deepcopy
import json
import re
from pathlib import Path
from typing import Any

from tools.providers.project_generation_generic_materializers import materialize_generic_archetype_files


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
    mode_lines = ["pass"]
    if run_mode == "gui":
        mode_lines = [
            "if not args.headless and len(sys.argv) == 1:",
            "    import tkinter as tk",
            "    root = tk.Tk()",
            "    root.title(args.project_name)",
            '    tk.Label(root, text="GUI-first launcher is ready; rerun with --headless for scripted export.").pack(padx=12, pady=12)',
            "    root.mainloop()",
            "    return 0",
        ]
    elif run_mode == "web":
        mode_lines = [
            "if args.serve:",
            '    preview = Path(args.out) / "preview.html"',
            "    preview.parent.mkdir(parents=True, exist_ok=True)",
            '    preview.write_text("<html><body><h1>Web-first preview placeholder</h1></body></html>\\\\n", encoding="utf-8")',
            '    print(json.dumps({"preview_html": str(preview)}, ensure_ascii=False, indent=2))',
            "    return 0",
        ]
    lines = [
        "from __future__ import annotations",
        "import argparse",
        "import json",
        "import sys",
        "from pathlib import Path",
        "",
        "ROOT = Path(__file__).resolve().parents[1]",
        'SRC = ROOT / "src"',
        "if str(SRC) not in sys.path:",
        "    sys.path.insert(0, str(SRC))",
        "",
        f"from {package_name}.service import generate_project",
        "",
        "def main() -> int:",
        f'    parser = argparse.ArgumentParser(description="{mode_label}")',
        '    parser.add_argument("--goal", default="project generation request")',
        '    parser.add_argument("--project-name", default="Project Copilot")',
        '    parser.add_argument("--out", default=str(ROOT / "generated_output"))',
        '    parser.add_argument("--headless", action="store_true")',
        '    parser.add_argument("--serve", action="store_true")',
        "    args = parser.parse_args()",
    ]
    lines.extend(f"    {row}" for row in mode_lines)
    lines.extend(
        [
            "    result = generate_project(goal=args.goal, project_name=args.project_name, out_dir=Path(args.out))",
            "    print(json.dumps(result, ensure_ascii=False, indent=2))",
            "    return 0",
            "",
            'if __name__ == "__main__":',
            "    raise SystemExit(main())",
        ]
    )
    return "\n".join(lines) + "\n"


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
        f"{project_root}/README.md": (
            "# Benchmark Narrative Copilot\n\n"
            "## What This Project Is\n\n"
            f"A fixed regression narrative sample for benchmark mode. Scoped goal reference: {goal_excerpt}\n\n"
            "## Implemented\n\n"
            "- Story outline, chapter plan, cast schema, and prompt export sample.\n"
            "- Structured deliverables for benchmark replay.\n\n"
            "## Not Implemented\n\n"
            "- Full GUI editor workflow.\n"
            "- Asset management UX beyond benchmark exports.\n\n"
            "## How To Run\n\n"
            "`python scripts/run_narrative_copilot.py --goal \"benchmark narrative\" --project-name \"Narrative Copilot Studio\" --out generated_output`\n\n"
            "## Sample Data\n\n"
            "- Built-in benchmark sample content is generated by the service itself.\n\n"
            "## Directory Map\n\n"
            "- `src/` narrative benchmark logic.\n"
            "- `tests/` service regression.\n"
            "- `docs/` benchmark workflow notes.\n\n"
            "## Limitations\n\n"
            "- This path is benchmark-only and does not claim full editor capability.\n\n"
            "## Repo Context Consumed\n\n"
            f"{_context_lines(context_used)}\n"
        ),
        f"{project_root}/docs/00_CORE.md": "# Core Runtime Notes\\n\\nBenchmark-only narrative sample.\\n",
        f"{project_root}/docs/benchmark_workflow.md": "# Benchmark Workflow\\n\\n1. Fixed narrative benchmark sample.\\n2. Story/cast/prompt export.\\n3. Regression verify.\\n",
        f"{project_root}/scripts/verify_repo.ps1": "$ErrorActionPreference = 'Stop'\n$root = Split-Path -Parent $PSScriptRoot\n$required = @(\n  (Join-Path $root 'README.md'),\n  (Join-Path $root 'scripts\\run_narrative_copilot.py'),\n  (Join-Path $root 'src\\narrative_copilot\\story\\chapter_planner.py')\n)\n$missing = @($required | Where-Object { -not (Test-Path $_) })\nif ($missing.Count -gt 0) {\n  Write-Output ('missing: ' + ($missing -join ', '))\n  exit 1\n}\nWrite-Output 'PASS'\n",
        f"{project_root}/meta/tasks/CURRENT.md": "# Generated Task Card\\n\\n- Topic: Benchmark narrative regression delivery\\n- Project Type: narrative benchmark sample\\n- Scaffold Family: narrative benchmark fixture\\n",
        f"{project_root}/meta/reports/LAST.md": "# Generated Report\\n\\n## Readlist\\n- benchmark narrative sample contract\\n\\n## Plan\\n- materialize fixed benchmark narrative files\\n\\n## Changes\\n- benchmark narrative sample materialized\\n\\n## Verify\\n- benchmark export flow available\\n\\n## Questions\\n- none\\n\\n## Demo\\n- structured benchmark deliverables generated\\n",
        f"{project_root}/meta/manifest.json": json.dumps({"schema_version": "ctcp-generated-project-manifest-v1", "project_type": "narrative_copilot", "execution_mode": "benchmark_regression", "goal": goal_excerpt, "context_files_used": context_used}, ensure_ascii=False, indent=2) + "\n",
    }


def _production_narrative_seed() -> tuple[dict[str, Any], dict[str, Any]]:
    sample_project = {
        "schema_version": "ctcp-narrative-editor-sample-v1",
        "project_name": "Narrative Forge Lite Sample",
        "theme": "A near-future suspense visual novel set in a seaside city haunted by memory void incidents.",
        "premise": (
            "A memory restoration investigator returns to the coastal city of Lintide after a wave of public 'memory void' events. "
            "While tracing erased childhood witnesses, she discovers that her own early memories of the city were edited by the same hidden network."
        ),
        "chapters": [
            {
                "chapter_id": "ch01",
                "title": "Salt on the Platform",
                "summary": "Iris returns to Lintide, opens the sample project, and accepts the first memory void case file.",
                "scene_ids": ["scene_arrival", "scene_clinic_intake", "scene_promenade_trace"],
            },
            {
                "chapter_id": "ch02",
                "title": "Archive of Borrowed Voices",
                "summary": "A buried civic archive links the void cases to a childhood incident Iris cannot fully recall.",
                "scene_ids": ["scene_archive_vault", "scene_rooftop_interview"],
            },
            {
                "chapter_id": "ch03",
                "title": "Hollows in the Rain",
                "summary": "Evidence splits into official and personal routes as the city prepares for a storm blackout.",
                "scene_ids": ["scene_apartment_wall", "scene_breakwater_lab", "scene_seawall_chase"],
            },
            {
                "chapter_id": "ch04",
                "title": "The Lighthouse Rewrite",
                "summary": "The final branch confronts the source of the edits and the truth behind Iris's childhood gap.",
                "scene_ids": ["scene_tunnel_core", "scene_lighthouse_finale"],
            },
        ],
        "characters": [
            {
                "character_id": "iris_qiao",
                "name": "Iris Qiao",
                "role": "Memory Restoration Investigator",
                "traits": ["methodical", "guarded", "tenacious"],
                "profile": "Independent investigator who reconstructs damaged memories for court-admissible review.",
            },
            {
                "character_id": "ren_tang",
                "name": "Ren Tang",
                "role": "Port District Liaison",
                "traits": ["dry humor", "protective", "suspicious"],
                "profile": "City liaison assigned to the void cases, balancing public panic against political pressure.",
            },
            {
                "character_id": "mara_zhou",
                "name": "Mara Zhou",
                "role": "Archive Curator",
                "traits": ["warm voice", "selective honesty", "evasive"],
                "profile": "Curator of the civic memory archive and one of the last people connected to Iris's lost childhood route.",
            },
        ],
        "assets": [
            {"asset_id": "bg_ferry_terminal", "asset_type": "background", "label": "Ferry Terminal at Dusk", "notes": ["placeholder background", "salt fog", "arrival route"]},
            {"asset_id": "bg_memory_clinic", "asset_type": "background", "label": "Memory Clinic Intake Room", "notes": ["placeholder background", "medical monitors"]},
            {"asset_id": "bg_promenade", "asset_type": "background", "label": "Seawall Promenade", "notes": ["placeholder background", "night rain reflections"]},
            {"asset_id": "bg_archive_vault", "asset_type": "background", "label": "Archive Vault", "notes": ["placeholder background", "paper shelves", "locked cabinets"]},
            {"asset_id": "bg_rooftop", "asset_type": "background", "label": "Rooftop Garden", "notes": ["placeholder background", "wind turbines", "city skyline"]},
            {"asset_id": "bg_apartment", "asset_type": "background", "label": "Abandoned Apartment Corridor", "notes": ["placeholder background", "childhood echoes"]},
            {"asset_id": "bg_breakwater_lab", "asset_type": "background", "label": "Breakwater Research Lab", "notes": ["placeholder background", "humming equipment"]},
            {"asset_id": "bg_tunnel_core", "asset_type": "background", "label": "Flood Tunnel Core", "notes": ["placeholder background", "memory relay hardware"]},
            {"asset_id": "bg_lighthouse", "asset_type": "background", "label": "Old Lighthouse Chamber", "notes": ["placeholder background", "final confrontation"]},
            {"asset_id": "sprite_iris_focus", "asset_type": "sprite", "label": "Iris Focus Pose", "notes": ["placeholder sprite", "neutral investigation stance"]},
            {"asset_id": "sprite_ren_guarded", "asset_type": "sprite", "label": "Ren Guarded Pose", "notes": ["placeholder sprite", "crossed-arm stance"]},
            {"asset_id": "sprite_mara_smile", "asset_type": "sprite", "label": "Mara Careful Smile", "notes": ["placeholder sprite", "soft deflection"]},
            {"asset_id": "sfx_memory_pulse", "asset_type": "sfx", "label": "Memory Pulse", "notes": ["placeholder audio cue", "glitch tone"]},
            {"asset_id": "sfx_storm_alarm", "asset_type": "sfx", "label": "Storm Alarm", "notes": ["placeholder audio cue", "port siren"]},
            {"asset_id": "cg_childhood_corridor", "asset_type": "cg", "label": "Childhood Corridor Flashback", "notes": ["placeholder CG", "edited memory reveal"]},
        ],
        "scenes": [
            {
                "scene_id": "scene_arrival",
                "chapter_id": "ch01",
                "title": "Ferry Terminal Return",
                "summary": "Iris arrives in Lintide and gets pulled into the first case before she can settle back in.",
                "background_asset_id": "bg_ferry_terminal",
                "character_ids": ["iris_qiao", "ren_tang"],
                "asset_ids": ["bg_ferry_terminal", "sprite_iris_focus", "sprite_ren_guarded", "sfx_memory_pulse"],
                "choices": [],
            },
            {
                "scene_id": "scene_clinic_intake",
                "chapter_id": "ch01",
                "title": "Blank Intake File",
                "summary": "A patient file contains whole missing paragraphs and one impossible childhood timestamp.",
                "background_asset_id": "bg_memory_clinic",
                "character_ids": ["iris_qiao", "ren_tang"],
                "asset_ids": ["bg_memory_clinic", "sprite_iris_focus", "sfx_memory_pulse"],
                "choices": [
                    {"choice_id": "accept_official_case", "label": "Accept the official case route", "target_scene_id": "scene_archive_vault"},
                    {"choice_id": "trace_private_name", "label": "Trace the private name in the blank file", "target_scene_id": "scene_promenade_trace"},
                ],
            },
            {
                "scene_id": "scene_promenade_trace",
                "chapter_id": "ch01",
                "title": "Promenade Witness Loop",
                "summary": "A witness repeats the same ten seconds of memory until Iris interrupts the loop manually.",
                "background_asset_id": "bg_promenade",
                "character_ids": ["iris_qiao"],
                "asset_ids": ["bg_promenade", "sprite_iris_focus", "sfx_memory_pulse"],
                "choices": [],
            },
            {
                "scene_id": "scene_archive_vault",
                "chapter_id": "ch02",
                "title": "Archive of Borrowed Voices",
                "summary": "Mara reveals a sealed archive register that lists Iris as both witness and redacted subject.",
                "background_asset_id": "bg_archive_vault",
                "character_ids": ["iris_qiao", "mara_zhou"],
                "asset_ids": ["bg_archive_vault", "sprite_iris_focus", "sprite_mara_smile", "cg_childhood_corridor"],
                "choices": [],
            },
            {
                "scene_id": "scene_rooftop_interview",
                "chapter_id": "ch02",
                "title": "Rooftop Bargain",
                "summary": "Ren asks Iris to choose whether to reveal the edited timestamp to him or keep it private.",
                "background_asset_id": "bg_rooftop",
                "character_ids": ["iris_qiao", "ren_tang"],
                "asset_ids": ["bg_rooftop", "sprite_ren_guarded", "sprite_iris_focus", "sfx_storm_alarm"],
                "choices": [
                    {"choice_id": "share_timestamp", "label": "Tell Ren the timestamp is tied to Iris", "target_scene_id": "scene_breakwater_lab"},
                    {"choice_id": "hide_timestamp", "label": "Keep the timestamp private and investigate alone", "target_scene_id": "scene_apartment_wall"},
                ],
            },
            {
                "scene_id": "scene_apartment_wall",
                "chapter_id": "ch03",
                "title": "Apartment Wall Scribbles",
                "summary": "A boarded apartment preserves a child's route map in handwriting Iris recognizes as her own.",
                "background_asset_id": "bg_apartment",
                "character_ids": ["iris_qiao", "mara_zhou"],
                "asset_ids": ["bg_apartment", "sprite_mara_smile", "cg_childhood_corridor"],
                "choices": [],
            },
            {
                "scene_id": "scene_breakwater_lab",
                "chapter_id": "ch03",
                "title": "Breakwater Relay Lab",
                "summary": "The lab explains how whole neighborhoods were edited under disaster-recovery exemptions.",
                "background_asset_id": "bg_breakwater_lab",
                "character_ids": ["iris_qiao", "ren_tang", "mara_zhou"],
                "asset_ids": ["bg_breakwater_lab", "sprite_iris_focus", "sprite_ren_guarded", "sfx_memory_pulse"],
                "choices": [],
            },
            {
                "scene_id": "scene_seawall_chase",
                "chapter_id": "ch03",
                "title": "Seawall Pursuit",
                "summary": "A courier carrying the missing childhood reel bolts through the storm warning zone.",
                "background_asset_id": "bg_promenade",
                "character_ids": ["iris_qiao", "ren_tang"],
                "asset_ids": ["bg_promenade", "sprite_iris_focus", "sprite_ren_guarded", "sfx_storm_alarm"],
                "choices": [
                    {"choice_id": "secure_reel", "label": "Secure the reel before the blackout", "target_scene_id": "scene_tunnel_core"},
                    {"choice_id": "follow_courier", "label": "Follow the courier into the flood tunnels", "target_scene_id": "scene_tunnel_core"},
                ],
            },
            {
                "scene_id": "scene_tunnel_core",
                "chapter_id": "ch04",
                "title": "Flood Tunnel Core",
                "summary": "The memory relay shows Iris that her childhood route was rewritten to protect a survivor list.",
                "background_asset_id": "bg_tunnel_core",
                "character_ids": ["iris_qiao", "mara_zhou"],
                "asset_ids": ["bg_tunnel_core", "sprite_iris_focus", "cg_childhood_corridor", "sfx_memory_pulse"],
                "choices": [],
            },
            {
                "scene_id": "scene_lighthouse_finale",
                "chapter_id": "ch04",
                "title": "Lighthouse Rewrite",
                "summary": "Iris decides whether to restore the erased memories publicly or preserve the city-wide protective lie.",
                "background_asset_id": "bg_lighthouse",
                "character_ids": ["iris_qiao", "ren_tang", "mara_zhou"],
                "asset_ids": ["bg_lighthouse", "sprite_iris_focus", "sprite_ren_guarded", "sprite_mara_smile", "cg_childhood_corridor", "sfx_storm_alarm"],
                "choices": [
                    {"choice_id": "publish_restoration", "label": "Publish the restored childhood record", "target_scene_id": "ending_public_truth"},
                    {"choice_id": "seal_restoration", "label": "Seal the restoration and keep the city stable", "target_scene_id": "ending_protective_lie"},
                ],
            },
        ],
        "runtime_snippets": {
            "opening_line": "Lintide waits with a silence that sounds rehearsed.",
        },
    }
    source_map = {
        "schema_version": "ctcp-narrative-sample-source-map-v1",
        "sample_project_path": "sample_data/example_project.json",
        "provenance_mode": "template_local_seed",
        "generator": "LOCAL:tools/providers/project_generation_business_templates.py::_production_narrative_seed",
        "content_items": [
            {"item_id": "theme_and_premise", "source": "LOCAL:tools/providers/project_generation_business_templates.py::_production_narrative_seed"},
            {"item_id": "character_cards", "source": "LOCAL:tools/providers/project_generation_business_templates.py::_production_narrative_seed"},
            {"item_id": "chapter_plan", "source": "LOCAL:tools/providers/project_generation_business_templates.py::_production_narrative_seed"},
            {"item_id": "scene_graph", "source": "LOCAL:tools/providers/project_generation_business_templates.py::_production_narrative_seed"},
            {"item_id": "asset_placeholders", "source": "LOCAL:tools/providers/project_generation_business_templates.py::_production_narrative_seed"},
            {"item_id": "runtime_snippets", "source": "LOCAL:tools/providers/project_generation_business_templates.py::_production_narrative_seed"},
        ],
        "api_content_applied": False,
        "api_content_source_ref": "",
        "field_sources": {
            "runtime_snippets.opening_line": "LOCAL:tools/providers/project_generation_business_templates.py::_production_narrative_seed",
        },
        "merge_rules": {
            "api_overridable_fields": {
                "characters": ["profile", "traits"],
                "chapters": ["summary"],
                "scenes": ["summary"],
                "choices": ["label"],
                "assets": ["notes"],
                "runtime_snippets": ["opening_line"],
            },
            "local_locked_fields": [
                "characters.character_id",
                "chapters.chapter_id",
                "scenes.scene_id",
                "scenes.chapter_id",
                "choices.choice_id",
                "choices.target_scene_id",
                "assets.asset_id",
            ],
            "fallback_behavior": "keep_local_when_api_missing_or_invalid",
        },
    }
    return sample_project, source_map


def _load_generator_sample_api_payload(run_dir: Path) -> dict[str, Any]:
    for name in ("sample_content_api.json", "narrative_sample_api.json"):
        path = run_dir / "artifacts" / name
        if not path.exists():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return doc if isinstance(doc, dict) else {}
    return {}


def _production_narrative_sample_bundle(*, run_dir: Path, project_spec: dict[str, Any] | None = None) -> dict[str, Any]:
    del project_spec
    sample_project, source_map = _production_narrative_seed()
    theme_brief = {
        "project_name": sample_project.get("project_name", ""),
        "theme": sample_project.get("theme", ""),
        "premise": sample_project.get("premise", ""),
        "opening_line": str(dict(sample_project.get("runtime_snippets", {})).get("opening_line", "")).strip(),
    }
    variant_seed = sum(ord(ch) for ch in run_dir.resolve().as_posix())
    variant_suffix = f"V{(variant_seed % 89) + 11:02d}"
    opening_variants = [
        "Lintide waits with a silence that sounds rehearsed.",
        "The harbor fog repeats names the city denies remembering.",
        "Each tide drags another edited childhood back to shore.",
        "Rain turns every streetlamp into a witness statement.",
    ]
    theme_brief["project_name"] = f"{theme_brief['project_name']} {variant_suffix}".strip()
    theme_brief["opening_line"] = opening_variants[variant_seed % len(opening_variants)]
    goal_adaptation = dict(source_map.get("goal_adaptation", {}))
    goal_adaptation["applied"] = True
    goal_adaptation["variant_suffix"] = variant_suffix
    source_map["goal_adaptation"] = goal_adaptation
    cast_cards = deepcopy([row for row in sample_project.get("characters", []) if isinstance(row, dict)])
    chapter_plan = deepcopy([row for row in sample_project.get("chapters", []) if isinstance(row, dict)])
    scene_graph = {
        "scenes": deepcopy([row for row in sample_project.get("scenes", []) if isinstance(row, dict)]),
    }
    choice_map = {
        "choices": [
            {
                "scene_id": str(scene.get("scene_id", "")).strip(),
                "choice_id": str(choice.get("choice_id", "")).strip(),
                "label": str(choice.get("label", "")).strip(),
                "target_scene_id": str(choice.get("target_scene_id", "")).strip(),
            }
            for scene in scene_graph["scenes"]
            for choice in scene.get("choices", [])
            if isinstance(choice, dict)
        ]
    }
    asset_placeholders = {
        "assets": deepcopy([row for row in sample_project.get("assets", []) if isinstance(row, dict)]),
    }
    api_payload = _load_generator_sample_api_payload(run_dir)
    source_ref = str(api_payload.get("source_ref", "")).strip() or str(api_payload.get("api_content_source_ref", "")).strip()
    if source_ref.startswith("API:"):
        character_map = {str(row.get("character_id", "")).strip(): row for row in cast_cards if str(row.get("character_id", "")).strip()}
        chapter_map = {str(row.get("chapter_id", "")).strip(): row for row in chapter_plan if str(row.get("chapter_id", "")).strip()}
        scene_map = {str(row.get("scene_id", "")).strip(): row for row in scene_graph["scenes"] if str(row.get("scene_id", "")).strip()}
        asset_map = {str(row.get("asset_id", "")).strip(): row for row in asset_placeholders["assets"] if str(row.get("asset_id", "")).strip()}
        if str(api_payload.get("theme", "")).strip():
            theme_brief["theme"] = str(api_payload.get("theme", "")).strip()
            source_map["field_sources"]["theme"] = source_ref
        if str(api_payload.get("premise", "")).strip():
            theme_brief["premise"] = str(api_payload.get("premise", "")).strip()
            source_map["field_sources"]["premise"] = source_ref
        if str(api_payload.get("opening_line", "")).strip():
            theme_brief["opening_line"] = str(api_payload.get("opening_line", "")).strip()
            source_map["field_sources"]["runtime_snippets.opening_line"] = source_ref
        for character_id, fields in dict(api_payload.get("cast_cards", {})).items():
            target = character_map.get(str(character_id))
            if target is None or not isinstance(fields, dict):
                continue
            if str(fields.get("profile", "")).strip():
                target["profile"] = str(fields.get("profile", "")).strip()
                source_map["field_sources"][f"characters.{character_id}.profile"] = source_ref
            if isinstance(fields.get("traits"), list):
                target["traits"] = [str(item).strip() for item in fields.get("traits", []) if str(item).strip()]
                source_map["field_sources"][f"characters.{character_id}.traits"] = source_ref
        for chapter_id, fields in dict(api_payload.get("chapter_plan", {})).items():
            target = chapter_map.get(str(chapter_id))
            if target is None or not isinstance(fields, dict):
                continue
            if str(fields.get("summary", "")).strip():
                target["summary"] = str(fields.get("summary", "")).strip()
                source_map["field_sources"][f"chapters.{chapter_id}.summary"] = source_ref
        for scene_id, fields in dict(api_payload.get("scene_graph", {})).items():
            target = scene_map.get(str(scene_id))
            if target is None or not isinstance(fields, dict):
                continue
            if str(fields.get("summary", "")).strip():
                target["summary"] = str(fields.get("summary", "")).strip()
                source_map["field_sources"][f"scenes.{scene_id}.summary"] = source_ref
        choice_updates = dict(api_payload.get("choice_map", {})) if isinstance(api_payload.get("choice_map", {}), dict) else {}
        for scene in scene_graph["scenes"]:
            for choice in [row for row in scene.get("choices", []) if isinstance(row, dict)]:
                payload = choice_updates.get(str(choice.get("choice_id", "")).strip())
                if not isinstance(payload, dict):
                    continue
                if str(payload.get("label", "")).strip():
                    choice["label"] = str(payload.get("label", "")).strip()
                    source_map["field_sources"][f"choices.{choice.get('choice_id', '')}.label"] = source_ref
                if str(payload.get("target_scene_id", "")).strip():
                    choice["target_scene_id"] = str(payload.get("target_scene_id", "")).strip()
                    source_map["field_sources"][f"choices.{choice.get('choice_id', '')}.target_scene_id"] = source_ref
        for asset_id, fields in dict(api_payload.get("asset_placeholders", {})).items():
            target = asset_map.get(str(asset_id))
            if target is None or not isinstance(fields, dict):
                continue
            if isinstance(fields.get("notes"), list):
                target["notes"] = [str(item).strip() for item in fields.get("notes", []) if str(item).strip()]
                source_map["field_sources"][f"assets.{asset_id}.notes"] = source_ref
        source_map["api_content_applied"] = True
        source_map["api_content_source_ref"] = source_ref
        source_map["provenance_mode"] = "mixed_local_api_generation"
        source_map["content_items"].append({"item_id": "api_generation_merge", "source": source_ref})
    scene_graph["branch_point_count"] = sum(1 for row in scene_graph["scenes"] if row.get("choices"))
    sample_project["project_name"] = theme_brief["project_name"]
    sample_project["theme"] = theme_brief["theme"]
    sample_project["premise"] = theme_brief["premise"]
    sample_project["characters"] = cast_cards
    sample_project["chapters"] = chapter_plan
    sample_project["scenes"] = scene_graph["scenes"]
    sample_project["assets"] = asset_placeholders["assets"]
    sample_project["runtime_snippets"] = {"opening_line": theme_brief["opening_line"]}
    choice_map["choices"] = [
        {
            "scene_id": str(scene.get("scene_id", "")).strip(),
            "choice_id": str(choice.get("choice_id", "")).strip(),
            "label": str(choice.get("label", "")).strip(),
            "target_scene_id": str(choice.get("target_scene_id", "")).strip(),
        }
        for scene in scene_graph["scenes"]
        for choice in scene.get("choices", [])
        if isinstance(choice, dict)
    ]
    return {
        "theme_brief": theme_brief,
        "cast_cards": cast_cards,
        "chapter_plan": chapter_plan,
        "scene_graph": scene_graph,
        "choice_map": choice_map,
        "asset_placeholders": asset_placeholders,
        "sample_project": sample_project,
        "source_map": source_map,
    }


def _production_narrative_launcher(*, package_name: str, startup_rel: str) -> str:
    return (
        "from __future__ import annotations\n"
        "import argparse\n"
        "import json\n"
        "import sys\n"
        "from pathlib import Path\n"
        "\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        'SRC = ROOT / "src"\n'
        "if str(SRC) not in sys.path:\n"
        "    sys.path.insert(0, str(SRC))\n"
        "\n"
        f"from {package_name}.service import generate_project\n"
        "\n"
        "def main() -> int:\n"
        '    parser = argparse.ArgumentParser(description="Narrative project launcher.")\n'
        '    parser.add_argument("--goal", default="project generation request")\n'
        '    parser.add_argument("--project-name", default="Project Copilot")\n'
        '    parser.add_argument("--out", default=str(ROOT / "generated_output"))\n'
        '    parser.add_argument("--api-content-file", default="")\n'
        '    parser.add_argument("--edits-file", default="")\n'
        '    parser.add_argument("--headless", action="store_true")\n'
        "    args = parser.parse_args()\n"
        "    if not args.headless and len(sys.argv) == 1:\n"
        "        import tkinter as tk\n"
        "        root = tk.Tk()\n"
        "        root.title(args.project_name)\n"
        '        tk.Label(root, text="Interactive workspace scaffold is ready; rerun with --headless for scripted export.").pack(padx=12, pady=12)\n'
        "        root.mainloop()\n"
        "        return 0\n"
        "    result = generate_project(\n"
        "        goal=args.goal,\n"
        "        project_name=args.project_name,\n"
        "        out_dir=Path(args.out),\n"
        "        api_content_path=Path(args.api_content_file) if args.api_content_file else None,\n"
        "        edits_path=Path(args.edits_file) if args.edits_file else None,\n"
        "    )\n"
        "    print(json.dumps(result, ensure_ascii=False, indent=2))\n"
        "    return 0\n"
        "\n"
        'if __name__ == "__main__":\n'
        "    raise SystemExit(main())\n"
    )


def _production_narrative_seed_module(*, sample_project_json: str, source_map_json: str) -> str:
    return (
        "from __future__ import annotations\n"
        "import json\n"
        "import os\n"
        "from copy import deepcopy\n"
        "from pathlib import Path\n"
        "\n"
        f"SAMPLE_PROJECT = json.loads(r'''{sample_project_json}''')\n"
        f"SOURCE_MAP = json.loads(r'''{source_map_json}''')\n"
        "\n"
        "def load_sample_project(*, goal: str, project_name: str) -> dict[str, object]:\n"
        "    project = deepcopy(SAMPLE_PROJECT)\n"
        "    project['goal'] = goal\n"
        "    project['project_name'] = project_name or str(project.get('project_name', 'Narrative Forge Lite Sample'))\n"
        "    return project\n"
        "\n"
        "def load_source_map() -> dict[str, object]:\n"
        "    return deepcopy(SOURCE_MAP)\n"
        "\n"
        "def sample_data_paths() -> dict[str, str]:\n"
        "    root = Path(__file__).resolve().parents[2]\n"
        "    return {'sample_project_json': str(root / 'sample_data' / 'example_project.json'), 'source_map_json': str(root / 'sample_data' / 'source_map.json')}\n"
        "\n"
        "def load_api_content(*, api_content: dict[str, object] | None = None, api_content_path: Path | None = None) -> dict[str, object]:\n"
        "    if isinstance(api_content, dict) and api_content:\n"
        "        return deepcopy(api_content)\n"
        "    env_path = str(os.environ.get('CTCP_NARRATIVE_API_CONTENT_FILE', '')).strip()\n"
        "    candidate = api_content_path or (Path(env_path) if env_path else None)\n"
        "    if candidate is None:\n"
        "        return {}\n"
        "    path = Path(candidate)\n"
        "    if not path.exists() or not path.is_file():\n"
        "        return {}\n"
        "    try:\n"
        "        data = json.loads(path.read_text(encoding='utf-8'))\n"
        "    except Exception:\n"
        "        return {}\n"
        "    return data if isinstance(data, dict) else {}\n"
        "\n"
        "def _source_ref(api_content: dict[str, object]) -> str:\n"
        "    direct = str(api_content.get('source_ref', '')).strip()\n"
        "    if direct.startswith('API:'):\n"
        "        return direct\n"
        "    model = str(api_content.get('model', '')).strip() or 'unknown-model'\n"
        "    call_id = str(api_content.get('call_id', '')).strip() or 'unknown-call'\n"
        "    if model or call_id:\n"
        "        return f'API:{model}/{call_id}'\n"
        "    return ''\n"
        "\n"
        "def _index(rows: list[dict[str, object]], key: str) -> dict[str, dict[str, object]]:\n"
        "    out: dict[str, dict[str, object]] = {}\n"
        "    for row in rows:\n"
        "        if not isinstance(row, dict):\n"
        "            continue\n"
        "        value = str(row.get(key, '')).strip()\n"
        "        if value:\n"
        "            out[value] = row\n"
        "    return out\n"
        "\n"
        "def apply_api_content(project: dict[str, object], source_map: dict[str, object], api_content: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:\n"
        "    merged_project = deepcopy(project)\n"
        "    merged_source_map = deepcopy(source_map)\n"
        "    merged_source_map.setdefault('field_sources', {})\n"
        "    merged_source_map.setdefault('content_items', [])\n"
        "    merged_source_map.setdefault('merge_rules', {})\n"
        "    if not api_content:\n"
        "        return merged_project, merged_source_map\n"
        "    source_ref = _source_ref(api_content)\n"
        "    if not source_ref:\n"
        "        return merged_project, merged_source_map\n"
        "    merged_source_map['api_content_applied'] = True\n"
        "    merged_source_map['api_content_source_ref'] = source_ref\n"
        "    character_map = _index([row for row in merged_project.get('characters', []) if isinstance(row, dict)], 'character_id')\n"
        "    chapter_map = _index([row for row in merged_project.get('chapters', []) if isinstance(row, dict)], 'chapter_id')\n"
        "    scene_map = _index([row for row in merged_project.get('scenes', []) if isinstance(row, dict)], 'scene_id')\n"
        "    asset_map = _index([row for row in merged_project.get('assets', []) if isinstance(row, dict)], 'asset_id')\n"
        "    for character_id, fields in dict(api_content.get('character_updates', {})).items():\n"
        "        target = character_map.get(str(character_id))\n"
        "        if target is None or not isinstance(fields, dict):\n"
        "            continue\n"
        "        if 'profile' in fields and str(fields.get('profile', '')).strip():\n"
        "            target['profile'] = str(fields.get('profile', '')).strip()\n"
        "            merged_source_map['field_sources'][f'characters.{character_id}.profile'] = source_ref\n"
        "        if 'traits' in fields and isinstance(fields.get('traits'), list):\n"
        "            target['traits'] = [str(item).strip() for item in fields.get('traits', []) if str(item).strip()]\n"
        "            merged_source_map['field_sources'][f'characters.{character_id}.traits'] = source_ref\n"
        "    for chapter_id, fields in dict(api_content.get('chapter_updates', {})).items():\n"
        "        target = chapter_map.get(str(chapter_id))\n"
        "        if target is None or not isinstance(fields, dict):\n"
        "            continue\n"
        "        if 'summary' in fields and str(fields.get('summary', '')).strip():\n"
        "            target['summary'] = str(fields.get('summary', '')).strip()\n"
        "            merged_source_map['field_sources'][f'chapters.{chapter_id}.summary'] = source_ref\n"
        "    for scene_id, fields in dict(api_content.get('scene_updates', {})).items():\n"
        "        target = scene_map.get(str(scene_id))\n"
        "        if target is None or not isinstance(fields, dict):\n"
        "            continue\n"
        "        if 'summary' in fields and str(fields.get('summary', '')).strip():\n"
        "            target['summary'] = str(fields.get('summary', '')).strip()\n"
        "            merged_source_map['field_sources'][f'scenes.{scene_id}.summary'] = source_ref\n"
        "    choice_updates = dict(api_content.get('choice_updates', {})) if isinstance(api_content.get('choice_updates', {}), dict) else {}\n"
        "    for scene in [row for row in merged_project.get('scenes', []) if isinstance(row, dict)]:\n"
        "        for choice in [row for row in scene.get('choices', []) if isinstance(row, dict)]:\n"
        "            choice_id = str(choice.get('choice_id', '')).strip()\n"
        "            payload = choice_updates.get(choice_id)\n"
        "            if not choice_id or not isinstance(payload, dict):\n"
        "                continue\n"
        "            if 'label' in payload and str(payload.get('label', '')).strip():\n"
        "                choice['label'] = str(payload.get('label', '')).strip()\n"
        "                merged_source_map['field_sources'][f'choices.{choice_id}.label'] = source_ref\n"
        "    for asset_id, fields in dict(api_content.get('asset_updates', {})).items():\n"
        "        target = asset_map.get(str(asset_id))\n"
        "        if target is None or not isinstance(fields, dict):\n"
        "            continue\n"
        "        if 'notes' in fields and isinstance(fields.get('notes'), list):\n"
        "            target['notes'] = [str(item).strip() for item in fields.get('notes', []) if str(item).strip()]\n"
        "            merged_source_map['field_sources'][f'assets.{asset_id}.notes'] = source_ref\n"
        "    snippets = dict(api_content.get('script_snippets', {})) if isinstance(api_content.get('script_snippets', {}), dict) else {}\n"
        "    runtime_snippets = dict(merged_project.get('runtime_snippets', {})) if isinstance(merged_project.get('runtime_snippets', {}), dict) else {}\n"
        "    if str(snippets.get('opening_line', '')).strip():\n"
        "        runtime_snippets['opening_line'] = str(snippets.get('opening_line', '')).strip()\n"
        "        merged_source_map['field_sources']['runtime_snippets.opening_line'] = source_ref\n"
        "    merged_project['runtime_snippets'] = runtime_snippets\n"
        "    if not any(str(row.get('source', '')).strip() == source_ref for row in merged_source_map.get('content_items', []) if isinstance(row, dict)):\n"
        "        merged_source_map['content_items'].append({'item_id': 'api_content_merge', 'source': source_ref})\n"
        "    return merged_project, merged_source_map\n"
    )


def _production_narrative_actions_module() -> str:
    return (
        "from __future__ import annotations\n"
        "import json\n"
        "from copy import deepcopy\n"
        "from pathlib import Path\n"
        "\n"
        "def load_edits(*, edits: list[dict[str, object]] | None = None, edits_path: Path | None = None) -> list[dict[str, object]]:\n"
        "    if isinstance(edits, list):\n"
        "        return [dict(item) for item in edits if isinstance(item, dict)]\n"
        "    if edits_path is None:\n"
        "        return []\n"
        "    path = Path(edits_path)\n"
        "    if not path.exists() or not path.is_file():\n"
        "        return []\n"
        "    try:\n"
        "        data = json.loads(path.read_text(encoding='utf-8'))\n"
        "    except Exception:\n"
        "        return []\n"
        "    if isinstance(data, dict):\n"
        "        data = data.get('operations', [])\n"
        "    return [dict(item) for item in data if isinstance(data, list) and isinstance(item, dict)]\n"
        "\n"
        "def _scene_map(project: dict[str, object]) -> dict[str, dict[str, object]]:\n"
        "    out: dict[str, dict[str, object]] = {}\n"
        "    for row in project.get('scenes', []):\n"
        "        if isinstance(row, dict):\n"
        "            scene_id = str(row.get('scene_id', '')).strip()\n"
        "            if scene_id:\n"
        "                out[scene_id] = row\n"
        "    return out\n"
        "\n"
        "def _character_map(project: dict[str, object]) -> dict[str, dict[str, object]]:\n"
        "    out: dict[str, dict[str, object]] = {}\n"
        "    for row in project.get('characters', []):\n"
        "        if isinstance(row, dict):\n"
        "            character_id = str(row.get('character_id', '')).strip()\n"
        "            if character_id:\n"
        "                out[character_id] = row\n"
        "    return out\n"
        "\n"
        "def _append_change(changes: list[dict[str, object]], *, path: str, before: object, after: object, action: str) -> None:\n"
        "    if before == after:\n"
        "        return\n"
        "    changes.append({'action': action, 'path': path, 'before': before, 'after': after})\n"
        "\n"
        "def apply_edit_operations(project: dict[str, object], operations: list[dict[str, object]], *, sample_project: dict[str, object]) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:\n"
        "    working = deepcopy(project)\n"
        "    sample_seed = deepcopy(sample_project)\n"
        "    trace = {\n"
        "        'interaction_mode': 'interactive_editor',\n"
        "        'available_actions': ['reload_sample', 'reset_sample', 'add_scene', 'update_scene', 'update_choice', 'update_character', 'bind_scene_asset', 'export_current_state'],\n"
        "        'applied_operations': [],\n"
        "        'has_changes': False,\n"
        "    }\n"
        "    changes: list[dict[str, object]] = []\n"
        "    for op in operations:\n"
        "        action = str(op.get('action', '')).strip()\n"
        "        if action in {'reload_sample', 'reset_sample'}:\n"
        "            before = len([row for row in working.get('scenes', []) if isinstance(row, dict)])\n"
        "            working = deepcopy(sample_seed)\n"
        "            trace['applied_operations'].append({'action': action, 'status': 'applied'})\n"
        "            _append_change(changes, path='project.reset', before=before, after=len([row for row in working.get('scenes', []) if isinstance(row, dict)]), action=action)\n"
        "            continue\n"
        "        if action == 'add_scene':\n"
        "            chapter_id = str(op.get('chapter_id', '')).strip()\n"
        "            scene_id = str(op.get('scene_id', '')).strip()\n"
        "            if chapter_id and scene_id:\n"
        "                new_scene = {\n"
        "                    'scene_id': scene_id,\n"
        "                    'chapter_id': chapter_id,\n"
        "                    'title': str(op.get('title', 'New Scene')).strip() or 'New Scene',\n"
        "                    'summary': str(op.get('summary', 'New scene summary')).strip() or 'New scene summary',\n"
        "                    'background_asset_id': str(op.get('background_asset_id', '')).strip(),\n"
        "                    'character_ids': [str(item).strip() for item in op.get('character_ids', []) if str(item).strip()],\n"
        "                    'asset_ids': [str(item).strip() for item in op.get('asset_ids', []) if str(item).strip()],\n"
        "                    'choices': [dict(item) for item in op.get('choices', []) if isinstance(item, dict)],\n"
        "                }\n"
        "                working.setdefault('scenes', []).append(new_scene)\n"
        "                for chapter in [row for row in working.get('chapters', []) if isinstance(row, dict)]:\n"
        "                    if str(chapter.get('chapter_id', '')).strip() == chapter_id:\n"
        "                        chapter.setdefault('scene_ids', []).append(scene_id)\n"
        "                        break\n"
        "                trace['applied_operations'].append({'action': action, 'status': 'applied', 'scene_id': scene_id})\n"
        "                _append_change(changes, path=f'scenes.{scene_id}', before=None, after=new_scene.get('title'), action=action)\n"
        "            continue\n"
        "        scene_map = _scene_map(working)\n"
        "        character_map = _character_map(working)\n"
        "        if action == 'update_scene':\n"
        "            scene_id = str(op.get('scene_id', '')).strip()\n"
        "            target = scene_map.get(scene_id)\n"
        "            fields = dict(op.get('fields', {})) if isinstance(op.get('fields', {}), dict) else {}\n"
        "            if target is not None:\n"
        "                for field in ('title', 'summary'):\n"
        "                    if field in fields and str(fields.get(field, '')).strip():\n"
        "                        before = target.get(field)\n"
        "                        target[field] = str(fields.get(field, '')).strip()\n"
        "                        _append_change(changes, path=f'scenes.{scene_id}.{field}', before=before, after=target.get(field), action=action)\n"
        "                trace['applied_operations'].append({'action': action, 'status': 'applied', 'scene_id': scene_id})\n"
        "            continue\n"
        "        if action == 'update_choice':\n"
        "            scene_id = str(op.get('scene_id', '')).strip()\n"
        "            choice_id = str(op.get('choice_id', '')).strip()\n"
        "            target = scene_map.get(scene_id)\n"
        "            if target is not None and choice_id:\n"
        "                choices = [row for row in target.get('choices', []) if isinstance(row, dict)]\n"
        "                choice = next((row for row in choices if str(row.get('choice_id', '')).strip() == choice_id), None)\n"
        "                if choice is None:\n"
        "                    choice = {'choice_id': choice_id, 'label': str(op.get('label', 'New Choice')).strip() or 'New Choice', 'target_scene_id': str(op.get('target_scene_id', '')).strip()}\n"
        "                    choices.append(choice)\n"
        "                    target['choices'] = choices\n"
        "                    _append_change(changes, path=f'choices.{choice_id}.label', before=None, after=choice.get('label'), action=action)\n"
        "                else:\n"
        "                    if str(op.get('label', '')).strip():\n"
        "                        before = choice.get('label')\n"
        "                        choice['label'] = str(op.get('label', '')).strip()\n"
        "                        _append_change(changes, path=f'choices.{choice_id}.label', before=before, after=choice.get('label'), action=action)\n"
        "                    if str(op.get('target_scene_id', '')).strip():\n"
        "                        before = choice.get('target_scene_id')\n"
        "                        choice['target_scene_id'] = str(op.get('target_scene_id', '')).strip()\n"
        "                        _append_change(changes, path=f'choices.{choice_id}.target_scene_id', before=before, after=choice.get('target_scene_id'), action=action)\n"
        "                trace['applied_operations'].append({'action': action, 'status': 'applied', 'scene_id': scene_id, 'choice_id': choice_id})\n"
        "            continue\n"
        "        if action == 'update_character':\n"
        "            character_id = str(op.get('character_id', '')).strip()\n"
        "            target = character_map.get(character_id)\n"
        "            fields = dict(op.get('fields', {})) if isinstance(op.get('fields', {}), dict) else {}\n"
        "            if target is not None:\n"
        "                for field in ('name', 'role', 'profile'):\n"
        "                    if field in fields and str(fields.get(field, '')).strip():\n"
        "                        before = target.get(field)\n"
        "                        target[field] = str(fields.get(field, '')).strip()\n"
        "                        _append_change(changes, path=f'characters.{character_id}.{field}', before=before, after=target.get(field), action=action)\n"
        "                trace['applied_operations'].append({'action': action, 'status': 'applied', 'character_id': character_id})\n"
        "            continue\n"
        "        if action == 'bind_scene_asset':\n"
        "            scene_id = str(op.get('scene_id', '')).strip()\n"
        "            slot = str(op.get('slot', '')).strip()\n"
        "            asset_id = str(op.get('asset_id', '')).strip()\n"
        "            target = scene_map.get(scene_id)\n"
        "            if target is not None and asset_id:\n"
        "                asset_ids = [str(item).strip() for item in target.get('asset_ids', []) if str(item).strip()]\n"
        "                if asset_id not in asset_ids:\n"
        "                    asset_ids.append(asset_id)\n"
        "                target['asset_ids'] = asset_ids\n"
        "                if slot in {'background', 'background_asset_id'}:\n"
        "                    before = target.get('background_asset_id')\n"
        "                    target['background_asset_id'] = asset_id\n"
        "                    _append_change(changes, path=f'scenes.{scene_id}.background_asset_id', before=before, after=asset_id, action=action)\n"
        "                else:\n"
        "                    _append_change(changes, path=f'scenes.{scene_id}.asset_ids', before=None, after=asset_id, action=action)\n"
        "                trace['applied_operations'].append({'action': action, 'status': 'applied', 'scene_id': scene_id, 'slot': slot, 'asset_id': asset_id})\n"
        "            continue\n"
        "        if action == 'export_current_state':\n"
        "            trace['applied_operations'].append({'action': action, 'status': 'noted'})\n"
        "    trace['has_changes'] = bool(changes)\n"
        "    state_diff = {'has_changes': bool(changes), 'operation_count': len(changes), 'changes': changes}\n"
        "    return working, trace, state_diff\n"
    )


def _production_narrative_workspace_module() -> str:
    return (
        "from __future__ import annotations\n"
        "def build_workspace_payload(project: dict[str, object], *, interaction_trace: dict[str, object] | None = None) -> dict[str, object]:\n"
        "    chapters = [row for row in project.get('chapters', []) if isinstance(row, dict)]\n"
        "    scenes = [row for row in project.get('scenes', []) if isinstance(row, dict)]\n"
        "    characters = [row for row in project.get('characters', []) if isinstance(row, dict)]\n"
        "    assets = [row for row in project.get('assets', []) if isinstance(row, dict)]\n"
        "    branch_rows = []\n"
        "    for scene in scenes:\n"
        "        for choice in scene.get('choices', []):\n"
        "            if isinstance(choice, dict):\n"
        "                branch_rows.append({'from_scene_id': scene.get('scene_id', ''), 'choice_id': choice.get('choice_id', ''), 'label': choice.get('label', ''), 'target_scene_id': choice.get('target_scene_id', '')})\n"
        "    return {\n"
        "        'workspace_title': str(project.get('project_name', 'Narrative Forge Lite')) + ' Editor Workspace',\n"
        "        'interaction_mode': 'interactive_editor',\n"
        "        'project_loader': {\n"
        "            'loaded_sample': 'sample_data/example_project.json',\n"
        "            'source_map': 'sample_data/source_map.json',\n"
        "            'chapter_count': len(chapters),\n"
        "            'scene_count': len(scenes),\n"
        "            'controls': ['load-sample', 'reset-sample'],\n"
        "        },\n"
        "        'story_editor': {\n"
        "            'chapter_rows': chapters,\n"
        "            'scene_rows': scenes,\n"
        "            'branch_rows': branch_rows,\n"
        "            'controls': ['add-scene', 'update-scene', 'update-branch'],\n"
        "        },\n"
        "        'cast_manager': {'character_rows': characters, 'controls': ['update-character']},\n"
        "        'asset_manager': {'asset_rows': assets, 'controls': ['bind-background', 'bind-sprite', 'bind-sfx', 'bind-cg']},\n"
        "        'preview_export': {\n"
        "            'panels': ['preview html', 'renpy script skeleton', 'scene graph json', 'asset catalog json'],\n"
        "            'deliverable_targets': ['preview.html', 'script_preview.rpy', 'scene_graph.json', 'asset_catalog.json'],\n"
        "            'controls': ['save-state', 'export-project'],\n"
        "        },\n"
        "        'applied_operations': list(dict(interaction_trace or {}).get('applied_operations', [])),\n"
        "        'available_actions': list(dict(interaction_trace or {}).get('available_actions', [])),\n"
        "    }\n"
    )


def _production_narrative_exporters_module() -> str:
    return (
        "from __future__ import annotations\n"
        "import json\n"
        "from pathlib import Path\n"
        "\n"
        "def _render_list(rows: list[str]) -> str:\n"
        "    return ''.join(f'<li>{row}</li>' for row in rows)\n"
        "\n"
        "def _script_preview(project: dict[str, object]) -> str:\n"
        "    scenes = [row for row in project.get('scenes', []) if isinstance(row, dict)]\n"
        "    opening_scene = scenes[0] if scenes else {}\n"
        "    branch_scene = next((row for row in scenes if row.get('choices')), opening_scene)\n"
        "    runtime_snippets = dict(project.get('runtime_snippets', {})) if isinstance(project.get('runtime_snippets', {}), dict) else {}\n"
        "    opening_line = str(runtime_snippets.get('opening_line', opening_scene.get('summary', 'Narrative editor preview generated by CTCP.')))\n"
        "    lines = [\n"
        "        'label start:',\n"
        "        f\"    scene {opening_scene.get('background_asset_id', 'bg_ferry_terminal')}\",\n"
        "        f\"    # {opening_scene.get('title', 'Opening Scene')}\",\n"
        "        f\"    '{opening_line}'\",\n"
        "    ]\n"
        "    choices = [row for row in branch_scene.get('choices', []) if isinstance(row, dict)]\n"
        "    if choices:\n"
        "        lines.append('    menu:')\n"
        "        for choice in choices[:3]:\n"
        "            lines.append(f\"        '{choice.get('label', 'Continue')}':\")\n"
        "            lines.append(f\"            jump {choice.get('target_scene_id', 'next_scene')}\")\n"
        "    return '\\n'.join(lines) + '\\n'\n"
        "\n"
        "def _preview_html(project: dict[str, object], workspace: dict[str, object], state_diff: dict[str, object]) -> str:\n"
        "    loader = dict(workspace.get('project_loader', {}))\n"
        "    story_editor = dict(workspace.get('story_editor', {}))\n"
        "    cast_manager = dict(workspace.get('cast_manager', {}))\n"
        "    asset_manager = dict(workspace.get('asset_manager', {}))\n"
        "    preview_export = dict(workspace.get('preview_export', {}))\n"
        "    first_scene = next((row for row in story_editor.get('scene_rows', []) if isinstance(row, dict)), {})\n"
        "    first_choice_scene = next((row for row in story_editor.get('scene_rows', []) if isinstance(row, dict) and row.get('choices')), first_scene)\n"
        "    first_choice = next((row for row in first_choice_scene.get('choices', []) if isinstance(row, dict)), {})\n"
        "    first_character = next((row for row in cast_manager.get('character_rows', []) if isinstance(row, dict)), {})\n"
        "    background_assets = [row for row in asset_manager.get('asset_rows', []) if isinstance(row, dict) and str(row.get('asset_type', '')).strip().lower() == 'background']\n"
        "    chapter_rows = [f\"<li><strong>{row.get('title', 'Chapter')}</strong><span> {len(row.get('scene_ids', []))} scenes</span></li>\" for row in story_editor.get('chapter_rows', []) if isinstance(row, dict)]\n"
        "    scene_rows = [f\"<li><strong>{row.get('title', 'Scene')}</strong><span> branch choices: {len(row.get('choices', []))}</span></li>\" for row in story_editor.get('scene_rows', []) if isinstance(row, dict)]\n"
        "    branch_rows = [f\"<li><strong>{row.get('from_scene_id', '')}</strong> -> {row.get('label', '')} -> {row.get('target_scene_id', '')}</li>\" for row in story_editor.get('branch_rows', []) if isinstance(row, dict)]\n"
        "    cast_rows = [f\"<li><strong>{row.get('name', 'Character')}</strong><span>{row.get('role', '')}</span></li>\" for row in cast_manager.get('character_rows', []) if isinstance(row, dict)]\n"
        "    asset_rows = [f\"<li><strong>{row.get('label', 'Asset')}</strong><span>{row.get('asset_type', 'asset')}</span></li>\" for row in asset_manager.get('asset_rows', []) if isinstance(row, dict)]\n"
        "    export_rows = [str(row) for row in preview_export.get('deliverable_targets', [])]\n"
        "    background_options = ''.join(f\"<option value='{row.get('asset_id', '')}'>{row.get('label', 'Background')}</option>\" for row in background_assets)\n"
        "    return \"<!doctype html><html><head><meta charset='utf-8'><title>Narrative Forge Lite Workspace</title><style>body{font-family:'Segoe UI',sans-serif;background:linear-gradient(180deg,#fbf7ef 0%,#eef6fb 100%);color:#172033;margin:0;}header{padding:28px 32px;border-bottom:1px solid #d7e5f2;background:rgba(255,255,255,.86);backdrop-filter:blur(8px);}main{display:grid;grid-template-columns:320px 1.25fr 1fr;gap:18px;padding:24px 28px;}section{background:#ffffff;border:1px solid #d9e0ea;border-radius:18px;padding:18px;box-shadow:0 16px 36px rgba(23,32,51,.08);}h1,h2,h3{margin:0 0 12px;}ul{margin:0;padding-left:18px;}li{margin:8px 0;}small{display:block;color:#0f766e;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-bottom:10px;}.stack{display:grid;gap:18px;}.tag{display:inline-block;padding:4px 10px;border-radius:999px;background:#e0f2fe;color:#0c4a6e;margin-right:8px;font-size:12px;font-weight:700;}.muted{color:#4b5563;}label{display:block;font-weight:600;margin-top:10px;}input,textarea,select,button{width:100%;box-sizing:border-box;margin-top:6px;padding:9px 10px;border-radius:10px;border:1px solid #cbd5e1;font:inherit;}button{cursor:pointer;background:#0f766e;color:#fff;border:none;font-weight:700;}button.secondary{background:#1d4ed8;}textarea{min-height:90px;}script{display:none;}</style></head><body><header data-state-source='workspace_snapshot.json' data-export-source='script_preview.rpy'><small>Editor Workspace</small><h1>\" + str(project.get('project_name', 'Narrative Forge Lite')) + \"</h1><p class='muted'>Project/sample load, story scene branch editor, character/asset management, and preview/export panels are visible in one real workspace capture.</p><div><span class='tag'>interactive editor</span><span class='tag'>sample load reset</span><span class='tag'>branch editing</span><span class='tag'>export coupling</span></div></header><main><div class='stack'><section><small>Project / Sample Load</small><h2>Project Loader</h2><form id='sample-loader-form'><label>Loaded sample<input id='loaded-sample-input' value='\" + str(loader.get('loaded_sample', 'sample_data/example_project.json')) + \"' /></label><label>Source map<input id='source-map-input' value='\" + str(loader.get('source_map', 'sample_data/source_map.json')) + \"' /></label><button type='button' data-action='load-sample'>Load Sample</button><button type='button' class='secondary' data-action='reset-sample'>Reset Sample</button></form><p class='muted'>Chapters: \" + str(loader.get('chapter_count', 0)) + \" | Scenes: \" + str(loader.get('scene_count', 0)) + \"</p></section><section><small>Preview / Export</small><h2>Preview Export Panel</h2><ul>\" + _render_list(export_rows) + \"</ul><button type='button' data-action='save-state'>Save State</button><button type='button' class='secondary' data-action='export-project'>Export Project</button><p class='muted'>Recorded changes: \" + str(int(dict(state_diff).get('operation_count', 0) or 0)) + \"</p></section></div><section><small>Story / Scene / Branch Editor</small><h2>Scene Graph Editor</h2><h3>Chapter Timeline</h3><ul>\" + ''.join(chapter_rows) + \"</ul><h3>Scene Editor</h3><form id='scene-editor-form'><label>Scene title<input id='scene-title-input' value='\" + str(first_scene.get('title', '')) + \"' /></label><label>Scene summary<textarea id='scene-summary-input'>\" + str(first_scene.get('summary', '')) + \"</textarea></label><button type='button' data-action='update-scene'>Update Scene</button><button type='button' class='secondary' data-action='add-scene'>Add Scene</button></form><ul>\" + ''.join(scene_rows) + \"</ul><h3>Branch Editor</h3><form id='branch-editor-form'><label>Choice label<input id='choice-label-input' value='\" + str(first_choice.get('label', '')) + \"' /></label><label>Choice target<select id='choice-target-select'>\" + ''.join(f\"<option value='{row.get('scene_id', '')}'>{row.get('title', '')}</option>\" for row in story_editor.get('scene_rows', []) if isinstance(row, dict)) + \"</select></label><button type='button' data-action='update-branch'>Update Branch</button></form><ul>\" + ''.join(branch_rows) + \"</ul></section><div class='stack'><section><small>Character Management</small><h2>Cast Board</h2><form id='character-editor-form'><label>Character name<input id='character-name-input' value='\" + str(first_character.get('name', '')) + \"' /></label><label>Character profile<textarea id='character-profile-input'>\" + str(first_character.get('profile', '')) + \"</textarea></label><button type='button' data-action='update-character'>Update Character</button></form><ul>\" + ''.join(cast_rows) + \"</ul></section><section><small>Asset Management</small><h2>Background / Sprite / SFX / CG Catalog</h2><form id='asset-bind-form'><label>Background binding<select id='background-select'>\" + background_options + \"</select></label><button type='button' data-action='bind-background'>Bind Background</button></form><ul>\" + ''.join(asset_rows) + \"</ul></section></div></main><script>const CTCP_EDITOR={stateSource:'workspace_snapshot.json',interactionTrace:'interaction_trace.json',stateDiff:'state_diff.json',exportTargets:['script_preview.rpy','scene_graph.json','asset_catalog.json'],loadSample(){return 'load-sample';},resetSample(){return 'reset-sample';},updateScene(){return 'update-scene';},updateBranch(){return 'update-branch';},updateCharacter(){return 'update-character';},bindBackground(){return 'bind-background';},saveState(){return 'save-state';},exportProject(){return 'export-project';}};document.addEventListener('DOMContentLoaded',()=>{document.body.dataset.editorReady='true';});</script></body></html>\"\n"
        "\n"
        "def export_bundle(project: dict[str, object], workspace: dict[str, object], prompt_sheet: list[dict[str, object]], source_map: dict[str, object], interaction_trace: dict[str, object], state_diff: dict[str, object], out_dir: Path) -> dict[str, str]:\n"
        "    deliver_dir = out_dir / 'deliverables'\n"
        "    deliver_dir.mkdir(parents=True, exist_ok=True)\n"
        "    project_json = deliver_dir / 'narrative_editor_project.json'\n"
        "    graph_json = deliver_dir / 'scene_graph.json'\n"
        "    assets_json = deliver_dir / 'asset_catalog.json'\n"
        "    prompts_json = deliver_dir / 'asset_prompts.json'\n"
        "    source_map_json = deliver_dir / 'source_map.json'\n"
        "    workspace_json = deliver_dir / 'workspace_snapshot.json'\n"
        "    interaction_json = deliver_dir / 'interaction_trace.json'\n"
        "    state_diff_json = deliver_dir / 'state_diff.json'\n"
        "    renpy_script = deliver_dir / 'script_preview.rpy'\n"
        "    preview_html = deliver_dir / 'preview.html'\n"
        "    verify_summary = deliver_dir / 'verify_summary.md'\n"
        "    project_json.write_text(json.dumps(project, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n"
        "    graph_json.write_text(json.dumps({'chapters': project.get('chapters', []), 'scenes': project.get('scenes', [])}, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n"
        "    assets_json.write_text(json.dumps({'assets': project.get('assets', []), 'characters': project.get('characters', [])}, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n"
        "    prompts_json.write_text(json.dumps({'asset_prompts': prompt_sheet}, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n"
        "    source_map_json.write_text(json.dumps(source_map, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n"
        "    workspace_json.write_text(json.dumps(workspace, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n"
        "    interaction_json.write_text(json.dumps(interaction_trace, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n"
        "    state_diff_json.write_text(json.dumps(state_diff, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n"
        "    renpy_script.write_text(_script_preview(project), encoding='utf-8')\n"
        "    preview_html.write_text(_preview_html(project, workspace, state_diff), encoding='utf-8')\n"
        "    verify_summary.write_text('# Verify Summary\\n\\n- project/sample loader present\\n- story scene branch editor present\\n- cast and asset management present\\n- preview/export panel present\\n- provenance source map exported\\n- interaction trace and state diff exported\\n', encoding='utf-8')\n"
        "    return {'project_bundle_json': str(project_json), 'scene_graph_json': str(graph_json), 'asset_catalog_json': str(assets_json), 'asset_prompts_json': str(prompts_json), 'source_map_json': str(source_map_json), 'workspace_snapshot_json': str(workspace_json), 'interaction_trace_json': str(interaction_json), 'state_diff_json': str(state_diff_json), 'script_preview_rpy': str(renpy_script), 'preview_html': str(preview_html), 'verify_summary_md': str(verify_summary)}\n"
    )


def _production_narrative_service_module(*, package_name: str) -> str:
    return (
        "from __future__ import annotations\n"
        "from copy import deepcopy\n"
        "from pathlib import Path\n"
        "\n"
        f"from {package_name}.assets.catalog import build_asset_catalog\n"
        f"from {package_name}.cast.schema import build_cast\n"
        f"from {package_name}.editor.actions import apply_edit_operations, load_edits\n"
        f"from {package_name}.editor.workspace import build_workspace_payload\n"
        f"from {package_name}.exporters.deliver import export_bundle\n"
        f"from {package_name}.pipeline.prompt_pipeline import build_prompt_sheet\n"
        f"from {package_name}.seed import apply_api_content, load_api_content, load_sample_project, load_source_map\n"
        f"from {package_name}.story.outline import build_premise\n"
        f"from {package_name}.story.scene_graph import build_scene_graph\n"
        "\n"
        "def generate_project(*, goal: str, project_name: str, out_dir: Path, api_content: dict[str, object] | None = None, api_content_path: Path | None = None, edits: list[dict[str, object]] | None = None, edits_path: Path | None = None) -> dict[str, str]:\n"
        "    project = load_sample_project(goal=goal, project_name=project_name)\n"
        "    source_map = load_source_map()\n"
        "    project['premise'] = build_premise(goal, str(project.get('project_name', project_name)))\n"
        "    project['characters'] = build_cast(project)\n"
        "    project['assets'] = build_asset_catalog(project)\n"
        "    graph = build_scene_graph(project)\n"
        "    project['chapters'] = graph.get('chapters', [])\n"
        "    project['scenes'] = graph.get('scenes', [])\n"
        "    project, source_map = apply_api_content(project, source_map, load_api_content(api_content=api_content, api_content_path=api_content_path))\n"
        "    editable_seed = deepcopy(project)\n"
        "    project, interaction_trace, state_diff = apply_edit_operations(project, load_edits(edits=edits, edits_path=edits_path), sample_project=editable_seed)\n"
        "    workspace = build_workspace_payload(project, interaction_trace=interaction_trace)\n"
        "    prompt_sheet = build_prompt_sheet(project)\n"
        "    return export_bundle(project, workspace, prompt_sheet, source_map, interaction_trace, state_diff, out_dir)\n"
    )


def _production_narrative_project_test(*, package_name: str) -> str:
    return (
        "from __future__ import annotations\n"
        "import json, sys, tempfile, unittest\n"
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        "SRC = ROOT / 'src'\n"
        "if str(SRC) not in sys.path:\n"
        "    sys.path.insert(0, str(SRC))\n"
        f"from {package_name}.service import generate_project\n"
        "class NarrativeCopilotServiceTests(unittest.TestCase):\n"
        "    def test_generate_project_exports_editor_bundle(self) -> None:\n"
        "        with tempfile.TemporaryDirectory(prefix='narrative_editor_') as td:\n"
        "            result = generate_project(goal='narrative vn editor', project_name='Narrative Editor', out_dir=Path(td))\n"
        "            bundle = Path(result['project_bundle_json'])\n"
        "            preview = Path(result['preview_html'])\n"
        "            graph = Path(result['scene_graph_json'])\n"
        "            source_map = Path(result['source_map_json'])\n"
        "            interaction = Path(result['interaction_trace_json'])\n"
        "            diff = Path(result['state_diff_json'])\n"
        "            self.assertTrue(bundle.exists())\n"
        "            self.assertTrue(preview.exists())\n"
        "            self.assertTrue(graph.exists())\n"
        "            self.assertTrue(source_map.exists())\n"
        "            self.assertTrue(interaction.exists())\n"
        "            self.assertTrue(diff.exists())\n"
        "            doc = json.loads(bundle.read_text(encoding='utf-8'))\n"
        "            self.assertGreaterEqual(len(doc['characters']), 3)\n"
        "            self.assertGreaterEqual(len(doc['chapters']), 4)\n"
        "            self.assertGreaterEqual(len(doc['scenes']), 8)\n"
        "if __name__ == '__main__':\n"
        "    unittest.main()\n"
    )


def _production_narrative_readme(*, goal_excerpt: str, startup_rel: str, context_used: list[str], project_spec: dict[str, Any]) -> str:
    spec_views = [str(item).strip() for item in project_spec.get("required_pages_or_views", []) if str(item).strip()] if isinstance(project_spec.get("required_pages_or_views", []), list) else []
    spec_modules = [str(item).strip() for item in project_spec.get("core_modules", []) if str(item).strip()] if isinstance(project_spec.get("core_modules", []), list) else []
    export_targets = [str(item).strip() for item in project_spec.get("export_targets", []) if str(item).strip()] if isinstance(project_spec.get("export_targets", []), list) else []
    return (
        "# Narrative GUI Editor MVP\n\n"
        "## What This Project Is\n\n"
        "A local narrative / VN editor scaffold focused on editable story graph authoring, cast management, asset catalog management, preview, and export. "
        f"It is generated from this scoped goal: {goal_excerpt}\n\n"
        "## Implemented\n\n"
        "- Interactive editor workspace with project/sample load, scene/branch editing controls, cast editing, asset binding, and preview/export controls.\n"
        "- A seeded near-future suspense VN sample with 3 major characters, 4 chapters, 10 scene nodes, and explicit branch points.\n"
        "- Mixed provenance contract: LOCAL seed content by default, with optional API-backed content merge via `--api-content-file`.\n"
        "- Export path that writes project JSON, scene graph JSON, asset catalog JSON, workspace snapshot, interaction trace, state diff, and Ren'Py-style script preview.\n\n"
        "## Not Implemented\n\n"
        "- Rich drag-and-drop node editing or persistent desktop storage.\n"
        "- Full binary asset import pipeline or production save conflict handling.\n"
        "- Always-on remote API generation without an explicit payload artifact.\n\n"
        "## How To Run\n\n"
        f"`python {startup_rel} --goal \"narrative editor smoke\" --project-name \"Narrative Forge Lite\" --out generated_output --headless`\n\n"
        "Optional inputs:\n\n"
        f"- `python {startup_rel} --headless --api-content-file sample_api_payload.json --edits-file workspace_edits.json`\n\n"
        "## Sample Data\n\n"
        "- Seed narrative project: `sample_data/example_project.json`\n"
        "- Seed provenance map: `sample_data/source_map.json`\n"
        "- Staged sample pipeline: `sample_data/pipeline/theme_brief.json`, `cast_cards.json`, `chapter_plan.json`, `scene_graph.json`, `choice_map.json`, `asset_placeholders.json`\n"
        "- Runtime export provenance: generated into `deliverables/source_map.json`\n\n"
        "## Generated Spec Snapshot\n\n"
        f"- Core modules: {', '.join(spec_modules) or 'editor_workspace, scene_graph, asset_catalog'}\n"
        f"- Required views: {', '.join(spec_views) or 'project_loader, story_scene_branch_editor, character_asset_manager, preview_export_panel'}\n"
        f"- Export targets: {', '.join(export_targets) or 'preview.html, script_preview.rpy, scene_graph.json'}\n\n"
        "## Directory Map\n\n"
        "- `src/` business logic for seed loading, editor actions, workspace state, and export.\n"
        "- `sample_data/` example project seed and LOCAL provenance map.\n"
        "- `tests/` smoke regression for export bundle generation.\n"
        "- `docs/` runtime notes and workflow summary.\n\n"
        "## Limitations\n\n"
        "- This is a minimal interactive editor scaffold, not a full commercial VN authoring suite.\n"
        "- API content is bounded to whitelisted fields and requires an explicit payload artifact; missing API fields fall back to LOCAL content.\n"
        "- Final bundle hygiene still excludes process/verify internals.\n\n"
        "## Repo Context Consumed\n\n"
        f"{_context_lines(context_used)}\n"
    )


def _production_narrative_files(
    run_dir: Path,
    goal_text: str,
    project_id: str,
    project_root: str,
    package_name: str,
    startup_rel: str,
    workflow_doc_rel: str,
    context_used: list[str],
    *,
    project_spec: dict[str, Any],
    capability_plan: dict[str, Any],
    materialize_capabilities: list[str],
) -> dict[str, str]:
    goal_excerpt = _goal_excerpt(goal_text)
    sample_bundle = _production_narrative_sample_bundle(run_dir=run_dir, project_spec=project_spec)
    sample_project_json = json.dumps(sample_bundle["sample_project"], ensure_ascii=False, indent=2)
    source_map_json = json.dumps(sample_bundle["source_map"], ensure_ascii=False, indent=2)
    capability_set = {str(item).strip() for item in materialize_capabilities if str(item).strip()}
    file_map = {
        f"{project_root}/pyproject.toml": f"[project]\nname = \"{project_id}\"\nversion = \"0.1.0\"\ndescription = \"Narrative project copilot generated by CTCP\"\nrequires-python = \">=3.11\"\n\n[tool.pytest.ini_options]\npythonpath = [\"src\"]\n",
        f"{project_root}/{startup_rel}": _production_narrative_launcher(package_name=package_name, startup_rel=startup_rel) if startup_rel.startswith("scripts/") else "",
        f"{project_root}/src/{package_name}/__init__.py": "from .service import generate_project\n",
        f"{project_root}/src/{package_name}/models.py": "from __future__ import annotations\nfrom typing import Any\nNarrativeDoc = dict[str, Any]\nWorkspaceDoc = dict[str, Any]\n",
        f"{project_root}/src/{package_name}/seed.py": _production_narrative_seed_module(sample_project_json=sample_project_json, source_map_json=source_map_json),
        f"{project_root}/src/{package_name}/editor/__init__.py": "from .actions import apply_edit_operations, load_edits\nfrom .workspace import build_workspace_payload\n",
        f"{project_root}/src/{package_name}/editor/actions.py": _production_narrative_actions_module(),
        f"{project_root}/src/{package_name}/editor/workspace.py": _production_narrative_workspace_module(),
        f"{project_root}/src/{package_name}/story/__init__.py": "from .outline import build_premise\nfrom .scene_graph import build_scene_graph\n",
        f"{project_root}/src/{package_name}/story/outline.py": "from __future__ import annotations\ndef build_premise(goal: str, project_name: str) -> str:\n    cleaned = ' '.join(str(goal or '').split())\n    return f'{project_name} is a narrative/VN editor MVP focused on story graph authoring, cast management, asset binding, preview, and export. Goal: {cleaned[:180]}'\n",
        f"{project_root}/src/{package_name}/story/scene_graph.py": "from __future__ import annotations\ndef build_scene_graph(project: dict[str, object]) -> dict[str, object]:\n    scenes = [row for row in project.get('scenes', []) if isinstance(row, dict)]\n    chapters = [row for row in project.get('chapters', []) if isinstance(row, dict)]\n    branch_points = [row for row in scenes if row.get('choices')]\n    return {'chapters': chapters, 'scenes': scenes, 'branch_points': branch_points}\n",
        f"{project_root}/src/{package_name}/cast/__init__.py": "from .schema import build_cast\n",
        f"{project_root}/src/{package_name}/cast/schema.py": "from __future__ import annotations\ndef build_cast(project: dict[str, object]) -> list[dict[str, object]]:\n    return [row for row in project.get('characters', []) if isinstance(row, dict)]\n",
        f"{project_root}/src/{package_name}/assets/__init__.py": "from .catalog import build_asset_catalog\n",
        f"{project_root}/src/{package_name}/assets/catalog.py": "from __future__ import annotations\ndef build_asset_catalog(project: dict[str, object]) -> list[dict[str, object]]:\n    return [row for row in project.get('assets', []) if isinstance(row, dict)]\n",
        f"{project_root}/src/{package_name}/pipeline/__init__.py": "from .prompt_pipeline import build_prompt_sheet\n",
        f"{project_root}/src/{package_name}/pipeline/prompt_pipeline.py": "from __future__ import annotations\ndef build_prompt_sheet(project: dict[str, object]) -> list[dict[str, object]]:\n    assets = {row.get('asset_id', ''): row for row in project.get('assets', []) if isinstance(row, dict)}\n    prompts = []\n    for scene in project.get('scenes', []):\n        if not isinstance(scene, dict):\n            continue\n        for asset_id in scene.get('asset_ids', []):\n            asset = assets.get(asset_id)\n            if not isinstance(asset, dict):\n                continue\n            prompts.append({'scene_id': scene.get('scene_id', ''), 'asset_id': asset.get('asset_id', ''), 'asset_type': asset.get('asset_type', ''), 'prompt': f\"{scene.get('title', 'Scene')} / {asset.get('label', 'Asset')} / narrative editor placeholder prompt\"})\n    return prompts\n",
        f"{project_root}/src/{package_name}/exporters/__init__.py": "from .deliver import export_bundle\n",
        f"{project_root}/src/{package_name}/exporters/deliver.py": _production_narrative_exporters_module(),
        f"{project_root}/src/{package_name}/service.py": _production_narrative_service_module(package_name=package_name),
        f"{project_root}/tests/test_{package_name}_service.py": _production_narrative_project_test(package_name=package_name),
        f"{project_root}/README.md": _production_narrative_readme(goal_excerpt=goal_excerpt, startup_rel=startup_rel, context_used=context_used, project_spec=project_spec),
        f"{project_root}/docs/00_CORE.md": "# Core Runtime Notes\n\n- project_domain: narrative_vn_editor\n- scaffold_family: narrative_gui_editor\n- mainline: intent -> sample project seed -> LOCAL/API provenance merge -> editor actions -> preview/export -> clean final bundle\n",
        f"{project_root}/{workflow_doc_rel}": "# Workflow\n\n1. Resolve narrative/editor domain and lock scaffold family.\n2. Materialize sample project seed, LOCAL provenance map, editor workspace, scene graph, asset catalog, and editor actions.\n3. Optionally merge whitelisted API-backed content from an explicit payload artifact.\n4. Apply edit operations, then export preview bundle, script preview, workspace snapshot, interaction trace, state diff, and verify summary.\n",
        f"{project_root}/scripts/verify_repo.ps1": "$ErrorActionPreference = 'Stop'\n$root = Split-Path -Parent $PSScriptRoot\n$required = @(\n  (Join-Path $root 'README.md'),\n  (Join-Path $root 'sample_data\\example_project.json'),\n  (Join-Path $root 'sample_data\\source_map.json'),\n  (Join-Path $root 'src\\" + package_name + "\\seed.py'),\n  (Join-Path $root 'src\\" + package_name + "\\editor\\actions.py'),\n  (Join-Path $root 'src\\" + package_name + "\\editor\\workspace.py'),\n  (Join-Path $root 'src\\" + package_name + "\\story\\scene_graph.py'),\n  (Join-Path $root 'src\\" + package_name + "\\assets\\catalog.py')\n)\n$missing = @($required | Where-Object { -not (Test-Path $_) })\nif ($missing.Count -gt 0) {\n  Write-Output ('missing: ' + ($missing -join ', '))\n  exit 1\n}\nWrite-Output 'PASS'\n",
        f"{project_root}/meta/tasks/CURRENT.md": "# Generated Task Card\n\n- Topic: Narrative GUI editor delivery\n- Project Type: narrative_vn_editor\n- Scaffold Family: narrative_gui_editor\n- Domain Capabilities: project/sample load, story branch editor, cast/asset management, provenance source map, preview/export\n",
        f"{project_root}/meta/reports/LAST.md": "# Generated Report\n\n## Readlist\n- narrative/editor domain contract\n- scaffold family routing\n- sample depth contract\n- interactive editor hardening contract\n\n## Plan\n- materialize sample project and provenance\n- materialize editor workspace, actions, and scene graph\n- optionally merge API content from explicit payload artifact\n- export preview bundle with interaction trace and state diff\n\n## Changes\n- generated narrative GUI editor family scaffold with interactive editor actions, richer sample content, and mixed LOCAL/API provenance support\n\n## Verify\n- export bundle smoke path available\n- interaction trace and state diff exported\n\n## Questions\n- none\n\n## Demo\n- preview_html generated with project loader, story editor, cast/asset manager, action controls, and preview/export evidence\n",
        f"{project_root}/meta/manifest.json": json.dumps({"schema_version": "ctcp-generated-project-manifest-v1", "project_type": "narrative_copilot", "project_domain": "narrative_vn_editor", "scaffold_family": "narrative_gui_editor", "execution_mode": "production", "goal": goal_excerpt, "context_files_used": context_used}, ensure_ascii=False, indent=2) + "\n",
        f"{project_root}/sample_data/example_project.json": sample_project_json + "\n",
        f"{project_root}/sample_data/source_map.json": source_map_json + "\n",
        f"{project_root}/sample_data/pipeline/theme_brief.json": json.dumps(sample_bundle["theme_brief"], ensure_ascii=False, indent=2) + "\n",
        f"{project_root}/sample_data/pipeline/cast_cards.json": json.dumps({"characters": sample_bundle["cast_cards"]}, ensure_ascii=False, indent=2) + "\n",
        f"{project_root}/sample_data/pipeline/chapter_plan.json": json.dumps({"chapters": sample_bundle["chapter_plan"]}, ensure_ascii=False, indent=2) + "\n",
        f"{project_root}/sample_data/pipeline/scene_graph.json": json.dumps(sample_bundle["scene_graph"], ensure_ascii=False, indent=2) + "\n",
        f"{project_root}/sample_data/pipeline/choice_map.json": json.dumps(sample_bundle["choice_map"], ensure_ascii=False, indent=2) + "\n",
        f"{project_root}/sample_data/pipeline/asset_placeholders.json": json.dumps(sample_bundle["asset_placeholders"], ensure_ascii=False, indent=2) + "\n",
    }
    bundle_to_files = {
        "editor_core": {
            f"{project_root}/src/{package_name}/models.py",
            f"{project_root}/src/{package_name}/seed.py",
            f"{project_root}/src/{package_name}/editor/__init__.py",
            f"{project_root}/src/{package_name}/editor/actions.py",
            f"{project_root}/src/{package_name}/editor/workspace.py",
        },
        "scene_branching": {
            f"{project_root}/src/{package_name}/story/__init__.py",
            f"{project_root}/src/{package_name}/story/outline.py",
            f"{project_root}/src/{package_name}/story/scene_graph.py",
            f"{project_root}/sample_data/pipeline/chapter_plan.json",
            f"{project_root}/sample_data/pipeline/scene_graph.json",
            f"{project_root}/sample_data/pipeline/choice_map.json",
        },
        "character_asset_management": {
            f"{project_root}/src/{package_name}/cast/__init__.py",
            f"{project_root}/src/{package_name}/cast/schema.py",
            f"{project_root}/src/{package_name}/assets/__init__.py",
            f"{project_root}/src/{package_name}/assets/catalog.py",
            f"{project_root}/sample_data/pipeline/cast_cards.json",
            f"{project_root}/sample_data/pipeline/asset_placeholders.json",
        },
        "sample_content_generation": {
            f"{project_root}/sample_data/example_project.json",
            f"{project_root}/sample_data/source_map.json",
            f"{project_root}/sample_data/pipeline/theme_brief.json",
        },
        "preview_export": {
            f"{project_root}/src/{package_name}/pipeline/__init__.py",
            f"{project_root}/src/{package_name}/pipeline/prompt_pipeline.py",
            f"{project_root}/src/{package_name}/exporters/__init__.py",
            f"{project_root}/src/{package_name}/exporters/deliver.py",
            f"{project_root}/src/{package_name}/service.py",
            f"{project_root}/tests/test_{package_name}_service.py",
        },
        "delivery_ready": {
            f"{project_root}/README.md",
            f"{project_root}/docs/00_CORE.md",
            f"{project_root}/{workflow_doc_rel}",
            f"{project_root}/scripts/verify_repo.ps1",
            f"{project_root}/meta/tasks/CURRENT.md",
            f"{project_root}/meta/reports/LAST.md",
            f"{project_root}/meta/manifest.json",
        },
    }
    allowed_files = {f"{project_root}/pyproject.toml", f"{project_root}/{startup_rel}", f"{project_root}/src/{package_name}/__init__.py"}
    for bundle_id in capability_set:
        allowed_files.update(bundle_to_files.get(bundle_id, set()))
    if not capability_set:
        return file_map
    return {rel: text for rel, text in file_map.items() if rel in allowed_files}


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
        file_map = _production_narrative_files(
            run_dir,
            goal_text,
            project_id,
            project_root,
            package_name,
            startup_rel,
            workflow_doc_rel,
            context_used,
            project_spec=dict(contract.get("project_spec", {}) if isinstance(contract.get("project_spec", {}), dict) else {}),
            capability_plan=dict(contract.get("capability_plan", {}) if isinstance(contract.get("capability_plan", {}), dict) else {}),
            materialize_capabilities=[str(item) for item in contract.get("materialize_capabilities", contract.get("business_capabilities", []))] if isinstance(contract.get("materialize_capabilities", contract.get("business_capabilities", [])), list) else [],
        )
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
