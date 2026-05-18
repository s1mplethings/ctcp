from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tools.providers.project_generation_blind_candidate import BLIND_CANDIDATE_PROJECTS, blind_candidate_files
from tools.providers.project_generation_medium_candidate import MEDIUM_CANDIDATE_PROJECTS, medium_candidate_files
from tools.providers.project_generation_provenance_writer import concrete_fast_path_provenance
from tools.providers.project_generation_template_writer import prefixed_files, standard_support_files


FULL_CANDIDATE_DOCS = {
    "live_provider_text_stats_cli": "docs/text_stats_workflow.md",
    "live_provider_password_policy_package": "docs/password_policy_workflow.md",
}


def _fallback_provenance(project_id: str) -> dict[str, Any]:
    if project_id in MEDIUM_CANDIDATE_PROJECTS:
        mode = "live_provider_medium_candidate"
    elif project_id in BLIND_CANDIDATE_PROJECTS:
        mode = "live_provider_blind_candidate"
    else:
        mode = "live_provider_full_candidate"
    base = concrete_fast_path_provenance(
        project_type=project_id,
        reason=f"bounded {mode} with deterministic validation, repair, and fallback",
    )
    base["generation_mode"] = mode
    if mode == "live_provider_blind_candidate":
        base["blind_case"] = True
        base["blind_case_name"] = project_id
    if mode == "live_provider_medium_candidate":
        base["medium_case"] = True
        base["medium_case_name"] = project_id
    return base


def _workflow_doc(project_id: str) -> str:
    if project_id in FULL_CANDIDATE_DOCS:
        return FULL_CANDIDATE_DOCS[project_id]
    if project_id in BLIND_CANDIDATE_PROJECTS:
        return str(BLIND_CANDIDATE_PROJECTS[project_id]["doc"])
    if project_id in MEDIUM_CANDIDATE_PROJECTS:
        return str(MEDIUM_CANDIDATE_PROJECTS[project_id]["doc"])
    return "docs/live_provider_candidate.md"


def _write_candidate(root: Path, files: dict[str, str]) -> None:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _run(cmd: list[str], cwd: Path, timeout: int = 30) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return {"exit_code": proc.returncode, "stdout": proc.stdout[-1000:], "stderr": proc.stderr[-1000:]}
    except subprocess.TimeoutExpired as exc:
        return {"exit_code": 124, "stdout": str(exc.stdout or "")[-1000:], "stderr": str(exc.stderr or "")[-1000:]}


def validate_candidate_runtime(project_id: str, files: dict[str, str]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"ctcp_live_candidate_{project_id}_") as tmp:
        root = Path(tmp)
        _write_candidate(root, files)
        tests = _run([sys.executable, "-m", "unittest", "discover", "-v"], root, timeout=45)
        if project_id == "live_provider_text_stats_cli":
            out = root / "stats.json"
            runtime = _run([sys.executable, "text_stats.py", "--input", "sample.txt", "--output", str(out)], root, timeout=20)
            data: dict[str, Any] = {}
            if out.exists():
                try:
                    data = json.loads(out.read_text(encoding="utf-8"))
                except Exception:
                    data = {}
            runtime_passed = (
                runtime["exit_code"] == 0
                and out.exists()
                and int(data.get("characters", -1)) > 0
                and int(data.get("words", -1)) >= 4
                and int(data.get("unique_words", -1)) >= 3
                and isinstance(data.get("top_words"), list)
            )
            import_valid = bool((root / "text_stats.py").exists())
        elif project_id == "live_provider_password_policy_package":
            script = (
                "from password_policy import validate_password, password_score, explain_password\n"
                "assert validate_password('StrongPass1!')['valid'] is True\n"
                "assert validate_password('weak')['valid'] is False\n"
                "assert password_score('StrongPass1!') > password_score('weak')\n"
                "assert explain_password('weak')\n"
            )
            runtime = _run([sys.executable, "-c", script], root, timeout=20)
            runtime_passed = runtime["exit_code"] == 0
            import_valid = runtime["exit_code"] == 0
        elif project_id == "live_provider_unit_converter_cli":
            runtime = _run([sys.executable, "unit_converter.py", "--from", "km", "--to", "miles", "--value", "1", "--json"], root, timeout=20)
            try:
                data = json.loads(runtime["stdout"])
            except Exception:
                data = {}
            runtime_passed = runtime["exit_code"] == 0 and abs(float(data.get("result", 0)) - 0.621371) < 0.01
            import_valid = (root / "unit_converter.py").exists()
        elif project_id == "live_provider_file_renamer_cli":
            with tempfile.TemporaryDirectory(prefix="ctcp_candidate_rename_") as rename_tmp:
                sample = Path(rename_tmp)
                (sample / "a.txt").write_text("a", encoding="utf-8")
                runtime = _run([sys.executable, "file_renamer.py", "--directory", str(sample), "--prefix", "pre_", "--dry-run"], root, timeout=20)
                runtime_passed = runtime["exit_code"] == 0 and "pre_a.txt" in runtime["stdout"] and (sample / "a.txt").exists() and not (sample / "pre_a.txt").exists()
            import_valid = (root / "file_renamer.py").exists()
        elif project_id == "live_provider_markdown_table_formatter":
            out = root / "table.md"
            runtime = _run([sys.executable, "markdown_table_formatter.py", "--input", "sample.csv", "--output", str(out)], root, timeout=20)
            text = out.read_text(encoding="utf-8") if out.exists() else ""
            runtime_passed = runtime["exit_code"] == 0 and "Name" in text and "Amount" in text and "Coffee" in text and "|" in text
            import_valid = (root / "markdown_table_formatter.py").exists()
        elif project_id == "live_provider_json_config_validator":
            script = (
                "from config_validator import validate_config, explain_errors\n"
                "valid = validate_config({'name': 'demo', 'enabled': True})\n"
                "assert valid['valid'] is True\n"
                "assert valid['config']['retries'] == 3\n"
                "bad = validate_config({'enabled': 'yes'})\n"
                "assert bad['valid'] is False and bad['errors']\n"
                "assert isinstance(explain_errors(bad['errors']), str)\n"
            )
            runtime = _run([sys.executable, "-c", script], root, timeout=20)
            runtime_passed = runtime["exit_code"] == 0
            import_valid = runtime["exit_code"] == 0
        elif project_id == "live_provider_static_site_generator":
            out_dir = root / "site_out"
            runtime = _run([sys.executable, "site_generator.py", "--input", "content", "--output", str(out_dir)], root, timeout=20)
            page = out_dir / "index.html"
            runtime_passed = runtime["exit_code"] == 0 and page.exists() and "<html" in page.read_text(encoding="utf-8").lower()
            import_valid = (root / "site_generator.py").exists()
        elif project_id == "live_provider_inventory_manager_app":
            runtime = _run([sys.executable, "-c", "import app, inventory_store"], root, timeout=20)
            script = (
                "from inventory_store import InventoryStore\n"
                "s=InventoryStore(':memory:')\n"
                "try:\n"
                "    p=s.create_product({'sku':'SKU1','name':'Widget','quantity':2,'reorder_level':5})\n"
                "except TypeError:\n"
                "    p=s.create_product('SKU1', 'Widget', 'Widget', 2, 5)\n"
                "assert p['id']\n"
                "assert len(s.list_products()) == 1\n"
                "try:\n"
                "    s.adjust_stock(p['id'], 3, 'restock')\n"
                "except TypeError:\n"
                "    s.adjust_stock(p['id'], 3)\n"
                "assert s.get_product(p['id'])['quantity'] == 5\n"
                "low = s.low_stock() if hasattr(s, 'low_stock') else s.list_low_stock()\n"
                "moves = s.movements() if hasattr(s, 'movements') else s.list_movements()\n"
                "assert isinstance(low, list)\n"
                "assert isinstance(moves, list)\n"
            )
            behavior = _run([sys.executable, "-c", script], root, timeout=20)
            runtime_passed = runtime["exit_code"] == 0 and behavior["exit_code"] == 0
            import_valid = runtime["exit_code"] == 0
            runtime = {"import": runtime, "behavior": behavior}
        elif project_id == "live_provider_knowledge_base_app":
            runtime = _run([sys.executable, "-c", "import app, kb_store"], root, timeout=20)
            script = (
                "from kb_store import KnowledgeBaseStore\n"
                "s=KnowledgeBaseStore(':memory:')\n"
                "try:\n"
                "    a=s.create_article({'title':'Install','body':'Install steps','tags':['setup','docs']})\n"
                "except TypeError:\n"
                "    a=s.create_article('Install', 'Install steps', ['setup','docs'])\n"
                "assert a['id']\n"
                "assert len(s.list_articles()) == 1\n"
                "assert s.search('install')\n"
                "assert 'setup' in s.tags()\n"
                "try:\n"
                "    s.update_article(a['id'], {'body':'Updated docs'})\n"
                "except TypeError:\n"
                "    s.update_article(a['id'], body='Updated docs')\n"
                "updated=s.get_article(a['id'])\n"
                "assert (updated.get('body') or updated.get('content')) == 'Updated docs'\n"
            )
            behavior = _run([sys.executable, "-c", script], root, timeout=20)
            runtime_passed = runtime["exit_code"] == 0 and behavior["exit_code"] == 0
            import_valid = runtime["exit_code"] == 0
            runtime = {"import": runtime, "behavior": behavior}
        elif project_id == "live_provider_event_booking_app":
            runtime = _run([sys.executable, "-c", "import app, event_store"], root, timeout=20)
            script = (
                "from event_store import EventStore\n"
                "s=EventStore(':memory:')\n"
                "e=s.create_event({'title':'Demo','date':'2026-01-01','capacity':1})\n"
                "assert e['id']\n"
                "assert len(s.list_events()) == 1\n"
                "b=s.create_booking(e['id'], {'attendee_name':'A','attendee_email':'a@example.test'})\n"
                "assert b['event_id'] == e['id']\n"
                "assert s.create_booking(e['id'], {'attendee_name':'B','attendee_email':'b@example.test'}).get('error') == 'capacity_exceeded'\n"
                "assert s.availability()[0]['remaining'] == 0\n"
            )
            behavior = _run([sys.executable, "-c", script], root, timeout=20)
            runtime_passed = runtime["exit_code"] == 0 and behavior["exit_code"] == 0
            import_valid = runtime["exit_code"] == 0
            runtime = {"import": runtime, "behavior": behavior}
        elif project_id == "live_provider_invoice_manager_app":
            runtime = _run([sys.executable, "-c", "import app, invoice_store"], root, timeout=20)
            script = (
                "from invoice_store import InvoiceStore\n"
                "s=InvoiceStore(':memory:')\n"
                "c=s.create_client({'name':'Acme','email':'a@example.test'})\n"
                "i=s.create_invoice({'client_id':c['id'],'number':'INV-1'})\n"
                "i=s.add_invoice_item(i['id'], {'description':'Work','quantity':2,'unit_price':50})\n"
                "assert i['subtotal'] == 100.0 and i['total'] == 110.0\n"
                "i=s.update_invoice_status(i['id'], 'sent')\n"
                "assert i['status'] == 'sent'\n"
                "assert s.summary()['invoice_count'] == 1\n"
            )
            behavior = _run([sys.executable, "-c", script], root, timeout=20)
            runtime_passed = runtime["exit_code"] == 0 and behavior["exit_code"] == 0
            import_valid = runtime["exit_code"] == 0
            runtime = {"import": runtime, "behavior": behavior}
        else:
            runtime = {"exit_code": 1, "stdout": "", "stderr": "unsupported_project"}
            runtime_passed = False
            import_valid = False
        return {
            "import_valid": import_valid,
            "generated_tests_passed": tests["exit_code"] == 0,
            "runtime_validation_passed": runtime_passed,
            "tests": tests,
            "runtime": runtime,
        }


def _deterministic_text_stats_files() -> dict[str, str]:
    return {
        "README.md": (
            "# live_provider_text_stats_cli\n\n"
            "## What This Project Is\nA small stdlib text statistics CLI.\n\n"
            "## Implemented\nCounts characters, words, lines, unique words, and top words.\n\n"
            "## Not Implemented\nNo server, network, or external package integration.\n\n"
            "## How To Run\n`python text_stats.py --input sample.txt --output stats.json`\n\n"
            "## Sample Data\n`sample.txt` contains a tiny input document.\n\n"
            "## Directory Map\n- `text_stats.py`: CLI and analyzer\n- `tests/`: unittest coverage\n\n"
            "## Limitations\nThis is a bounded local project candidate.\n"
        ),
        "sample.txt": "Hello world hello\nThis is a small text stats sample.\n",
        "text_stats.py": (
            "from __future__ import annotations\n\nimport argparse, json, re\nfrom collections import Counter\nfrom pathlib import Path\n\n"
            "def analyze_text(text: str) -> dict[str, object]:\n"
            "    words = re.findall(r\"[A-Za-z0-9']+\", text.lower())\n"
            "    counts = Counter(words)\n"
            "    return {'characters': len(text), 'words': len(words), 'lines': len(text.splitlines()), 'unique_words': len(counts), 'top_words': counts.most_common(5)}\n\n"
            "def main(argv: list[str] | None = None) -> int:\n"
            "    parser = argparse.ArgumentParser()\n"
            "    parser.add_argument('--input')\n"
            "    parser.add_argument('--output')\n"
            "    parser.add_argument('--goal')\n"
            "    parser.add_argument('--project-name')\n"
            "    parser.add_argument('--out')\n"
            "    args, _unknown = parser.parse_known_args(argv)\n"
            "    if args.out and not args.input:\n"
            "        Path(args.out).mkdir(parents=True, exist_ok=True)\n"
            "        (Path(args.out) / 'deliverable.json').write_text(json.dumps({'status': 'ok', 'project': args.project_name or 'text_stats'}), encoding='utf-8')\n"
            "        return 0\n"
            "    if not args.input or not args.output:\n"
            "        parser.error('the following arguments are required: --input, --output')\n"
            "    data = analyze_text(Path(args.input).read_text(encoding='utf-8'))\n"
            "    Path(args.output).write_text(json.dumps(data, indent=2), encoding='utf-8')\n"
            "    return 0\n\n"
            "if __name__ == '__main__':\n"
            "    raise SystemExit(main())\n"
        ),
        "tests/__init__.py": "# unittest package marker\n",
        "tests/test_text_stats.py": (
            "import json, tempfile, unittest\nfrom pathlib import Path\nfrom text_stats import analyze_text, main\n\n"
            "class TextStatsTests(unittest.TestCase):\n"
            "    def test_analyze_text_counts(self):\n"
            "        data = analyze_text('Hello hello\\nworld')\n"
            "        self.assertEqual(data['words'], 3)\n"
            "        self.assertEqual(data['unique_words'], 2)\n"
            "    def test_cli_writes_json(self):\n"
            "        with tempfile.TemporaryDirectory() as tmp:\n"
            "            inp = Path(tmp) / 'in.txt'; out = Path(tmp) / 'out.json'\n"
            "            inp.write_text('A a b', encoding='utf-8')\n"
            "            self.assertEqual(main(['--input', str(inp), '--output', str(out)]), 0)\n"
            "            self.assertEqual(json.loads(out.read_text())['words'], 3)\n"
            "if __name__ == '__main__': unittest.main()\n"
        ),
    }


def _deterministic_password_files() -> dict[str, str]:
    return {
        "README.md": (
            "# live_provider_password_policy_package\n\n"
            "## What This Project Is\nA small stdlib password policy package.\n\n"
            "## Implemented\nValidation, scoring, and password explanations.\n\n"
            "## Not Implemented\nNo external auth service or password storage.\n\n"
            "## How To Run\n`python -m unittest discover -v`\n\n"
            "## Sample Data\nTests include strong and weak password examples.\n\n"
            "## Directory Map\n- `password_policy/`: package source\n- `tests/`: unittest coverage\n\n"
            "## Limitations\nThis is a local package candidate, not a production auth system.\n"
        ),
        "password_policy/__init__.py": (
            "try:\n"
            "    from .policy import explain_password, password_score, validate_password\n"
            "except ImportError:\n"
            "    from policy import explain_password, password_score, validate_password\n"
            "__all__ = ['validate_password', 'password_score', 'explain_password']\n"
            "if __name__ == '__main__':\n"
            "    print('password_policy package ready')\n"
        ),
        "password_policy/policy.py": (
            "from __future__ import annotations\n\nimport string\n\n"
            "DEFAULT_POLICY = {'min_length': 8, 'uppercase': True, 'lowercase': True, 'digit': True, 'symbol': True}\n\n"
            "def _checks(password: str, policy: dict[str, object]) -> dict[str, bool]:\n"
            "    return {\n"
            "        'min_length': len(password) >= int(policy.get('min_length', 8)),\n"
            "        'uppercase': any(ch.isupper() for ch in password) if policy.get('uppercase', True) else True,\n"
            "        'lowercase': any(ch.islower() for ch in password) if policy.get('lowercase', True) else True,\n"
            "        'digit': any(ch.isdigit() for ch in password) if policy.get('digit', True) else True,\n"
            "        'symbol': any(ch in string.punctuation for ch in password) if policy.get('symbol', True) else True,\n"
            "    }\n\n"
            "def validate_password(password: str, policy: dict[str, object] | None = None) -> dict[str, object]:\n"
            "    active = dict(DEFAULT_POLICY); active.update(policy or {})\n"
            "    checks = _checks(str(password or ''), active)\n"
            "    return {'valid': all(checks.values()), 'checks': checks, 'score': password_score(password)}\n\n"
            "def password_score(password: str) -> int:\n"
            "    pwd = str(password or '')\n"
            "    return min(100, len(pwd) * 4 + sum(15 for ok in _checks(pwd, DEFAULT_POLICY).values() if ok))\n\n"
            "def explain_password(password: str) -> list[str]:\n"
            "    result = validate_password(password)\n"
            "    return [name for name, ok in result['checks'].items() if not ok]\n"
        ),
        "tests/__init__.py": "# unittest package marker\n",
        "tests/test_policy.py": (
            "import unittest\nfrom password_policy import explain_password, password_score, validate_password\n\n"
            "class PasswordPolicyTests(unittest.TestCase):\n"
            "    def test_valid_password(self):\n"
            "        self.assertTrue(validate_password('StrongPass1!')['valid'])\n"
            "    def test_weak_password(self):\n"
            "        result = validate_password('weak')\n"
            "        self.assertFalse(result['valid'])\n"
            "        self.assertIn('min_length', explain_password('weak'))\n"
            "    def test_score_orders_strength(self):\n"
            "        self.assertGreater(password_score('StrongPass1!'), password_score('weak'))\n"
            "if __name__ == '__main__': unittest.main()\n"
        ),
    }


def deterministic_candidate_files(project_id: str, project_root: str, goal_text: str, project_archetype: str = "cli_toolkit") -> dict[str, str]:
    if project_id == "live_provider_text_stats_cli":
        files = _deterministic_text_stats_files()
        run = "python text_stats.py --input sample.txt --output stats.json"
    elif project_id == "live_provider_password_policy_package":
        files = _deterministic_password_files()
        run = "python -m unittest discover -v"
    else:
        files = medium_candidate_files(project_id) if project_id in MEDIUM_CANDIDATE_PROJECTS else blind_candidate_files(project_id)
        run = "python -m unittest discover -v"
    provenance = _fallback_provenance(project_id)
    provenance["provider_authorship"] = "not_claimed"
    support = standard_support_files(
        project_id=project_id,
        workflow_doc_rel=_workflow_doc(project_id),
        provenance=provenance,
        core_notes=f"# Core Runtime Notes\n\n- project_id: {project_id}\n- generation_mode: {provenance['generation_mode']} fallback\n",
        workflow_notes=f"# Workflow\n\n- Run: `{run}`\n- Generated through ordinary CTCP mainline.\n",
        project_archetype=project_archetype,
    )
    return prefixed_files(project_root, {**files, **support})



