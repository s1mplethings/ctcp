from __future__ import annotations

from typing import Any


BLIND_CANDIDATE_PROJECTS: dict[str, dict[str, Any]] = {
    "live_provider_unit_converter_cli": {
        "keywords": ("live_provider_unit_converter_cli", "unit converter cli", "km to miles", "celsius to fahrenheit", "kg to lb"),
        "required": ("live_provider_blind_candidate",),
        "startup": "unit_converter.py",
        "doc": "docs/unit_converter_workflow.md",
        "business": ["README.md", "unit_converter.py", "tests/test_unit_converter.py", "provenance.json"],
        "description": "Live Provider Unit Converter CLI",
        "task": (
            "Build a Python stdlib-only argparse CLI in unit_converter.py. Support --from, --to, --value, and --json. "
            "Conversions: km/miles, celsius/fahrenheit, kg/lb. JSON output must include input_value, from_unit, to_unit, result."
        ),
    },
    "live_provider_file_renamer_cli": {
        "keywords": ("live_provider_file_renamer_cli", "file renamer dry-run", "rename files by prefix", "dry-run mode"),
        "required": ("live_provider_blind_candidate",),
        "startup": "file_renamer.py",
        "doc": "docs/file_renamer_workflow.md",
        "business": ["README.md", "file_renamer.py", "tests/test_file_renamer.py", "provenance.json"],
        "description": "Live Provider File Renamer Dry-Run CLI",
        "task": (
            "Build a Python stdlib-only argparse CLI in file_renamer.py. Support --directory, --prefix, --suffix, and --dry-run. "
            "Dry-run must print planned renames and must not rename files. Reject parent traversal and stay inside the supplied directory."
        ),
    },
    "live_provider_markdown_table_formatter": {
        "keywords": ("live_provider_markdown_table_formatter", "markdown table formatter", "csv to markdown table", "align columns"),
        "required": ("live_provider_blind_candidate",),
        "startup": "markdown_table_formatter.py",
        "doc": "docs/markdown_table_formatter_workflow.md",
        "business": ["README.md", "markdown_table_formatter.py", "sample.csv", "tests/test_markdown_table_formatter.py", "provenance.json"],
        "description": "Live Provider Markdown Table Formatter",
        "task": (
            "Build a Python stdlib-only CLI in markdown_table_formatter.py. Support --input CSV and --output markdown file. "
            "Convert the CSV header and rows into an aligned markdown table."
        ),
    },
    "live_provider_json_config_validator": {
        "keywords": ("live_provider_json_config_validator", "json config validator", "required fields", "default values"),
        "required": ("live_provider_blind_candidate",),
        "startup": "config_validator/__init__.py",
        "doc": "docs/json_config_validator_workflow.md",
        "business": ["README.md", "config_validator/__init__.py", "config_validator/validator.py", "tests/test_validator.py", "provenance.json"],
        "description": "Live Provider JSON Config Validator Package",
        "task": (
            "Build a Python stdlib-only importable package config_validator. Implement validate_config(config, schema=None), "
            "load_and_validate(path, schema=None), and explain_errors(errors). Validate required fields, types, defaults, and errors."
        ),
    },
    "live_provider_static_site_generator": {
        "keywords": ("live_provider_static_site_generator", "simple static site generator", "markdown-like text", "index page"),
        "required": ("live_provider_blind_candidate",),
        "startup": "site_generator.py",
        "doc": "docs/static_site_generator_workflow.md",
        "business": ["README.md", "site_generator.py", "content/index.txt", "tests/test_site_generator.py", "provenance.json"],
        "description": "Live Provider Static Site Generator",
        "task": (
            "Build a Python stdlib-only CLI in site_generator.py. Support --input directory and --output directory. "
            "Read markdown-like .txt files, write simple HTML pages, and generate index.html. Do not write outside the output directory."
        ),
    },
}


def _unit_converter_files() -> dict[str, str]:
    return {
        "README.md": "# live_provider_unit_converter_cli\n\nRun: `python unit_converter.py --from km --to miles --value 1 --json`.\n",
        "unit_converter.py": (
            "from __future__ import annotations\n\nimport argparse, json\n\n"
            "FACTORS = {('km','miles'): 0.621371, ('miles','km'): 1.609344, ('kg','lb'): 2.2046226218, ('lb','kg'): 0.45359237}\n"
            "def convert(value: float, from_unit: str, to_unit: str) -> float:\n"
            "    f, t = from_unit.lower(), to_unit.lower()\n"
            "    if (f, t) in FACTORS: return value * FACTORS[(f, t)]\n"
            "    if f == 'celsius' and t == 'fahrenheit': return value * 9 / 5 + 32\n"
            "    if f == 'fahrenheit' and t == 'celsius': return (value - 32) * 5 / 9\n"
            "    raise ValueError(f'unsupported conversion: {from_unit} to {to_unit}')\n\n"
            "def main(argv=None):\n"
            "    p = argparse.ArgumentParser(); p.add_argument('--from', dest='from_unit', required=True); p.add_argument('--to', dest='to_unit', required=True); p.add_argument('--value', type=float, required=True); p.add_argument('--json', action='store_true')\n"
            "    a = p.parse_args(argv); result = convert(a.value, a.from_unit, a.to_unit); payload = {'input_value': a.value, 'from_unit': a.from_unit, 'to_unit': a.to_unit, 'result': result}\n"
            "    print(json.dumps(payload) if a.json else result); return 0\n\n"
            "if __name__ == '__main__': raise SystemExit(main())\n"
        ),
        "tests/__init__.py": "# unittest package marker\n",
        "tests/test_unit_converter.py": (
            "import json, subprocess, sys, unittest\nfrom unit_converter import convert\n\n"
            "class UnitConverterTests(unittest.TestCase):\n"
            "    def test_known_conversions(self):\n"
            "        self.assertAlmostEqual(convert(1, 'km', 'miles'), 0.621371, places=4)\n"
            "        self.assertAlmostEqual(convert(32, 'fahrenheit', 'celsius'), 0.0, places=4)\n"
            "    def test_json_cli(self):\n"
            "        p = subprocess.run([sys.executable, 'unit_converter.py', '--from', 'kg', '--to', 'lb', '--value', '2', '--json'], capture_output=True, text=True)\n"
            "        self.assertEqual(p.returncode, 0); self.assertAlmostEqual(json.loads(p.stdout)['result'], 4.409245, places=3)\n"
            "if __name__ == '__main__': unittest.main()\n"
        ),
    }


def _file_renamer_files() -> dict[str, str]:
    return {
        "README.md": "# live_provider_file_renamer_cli\n\nRun dry-run: `python file_renamer.py --directory sample --prefix pre_ --dry-run`.\n",
        "file_renamer.py": (
            "from __future__ import annotations\n\nimport argparse\nfrom pathlib import Path\n\n"
            "def _safe_directory(path: str) -> Path:\n"
            "    p = Path(path).resolve()\n"
            "    if '..' in Path(path).parts or not p.exists() or not p.is_dir(): raise ValueError('unsafe directory')\n"
            "    return p\n\n"
            "def planned_renames(directory: str, prefix: str = '', suffix: str = '') -> list[tuple[Path, Path]]:\n"
            "    root = _safe_directory(directory); out = []\n"
            "    for src in sorted(p for p in root.iterdir() if p.is_file()):\n"
            "        dst = root / f'{prefix}{src.stem}{suffix}{src.suffix}'\n"
            "        if dst.resolve().parent != root: raise ValueError('unsafe target')\n"
            "        out.append((src, dst))\n"
            "    return out\n\n"
            "def main(argv=None):\n"
            "    p = argparse.ArgumentParser(); p.add_argument('--directory', required=True); p.add_argument('--prefix', default=''); p.add_argument('--suffix', default=''); p.add_argument('--dry-run', action='store_true')\n"
            "    a = p.parse_args(argv); rows = planned_renames(a.directory, a.prefix, a.suffix)\n"
            "    for src, dst in rows: print(f'{src.name} -> {dst.name}')\n"
            "    if not a.dry_run:\n"
            "        for src, dst in rows: src.rename(dst)\n"
            "    return 0\n\n"
            "if __name__ == '__main__': raise SystemExit(main())\n"
        ),
        "tests/__init__.py": "# unittest package marker\n",
        "tests/test_file_renamer.py": (
            "import tempfile, unittest\nfrom pathlib import Path\nfrom file_renamer import main, planned_renames\n\n"
            "class FileRenamerTests(unittest.TestCase):\n"
            "    def test_dry_run_does_not_rename(self):\n"
            "        with tempfile.TemporaryDirectory() as tmp:\n"
            "            p = Path(tmp) / 'a.txt'; p.write_text('x')\n"
            "            self.assertEqual(main(['--directory', tmp, '--prefix', 'pre_', '--dry-run']), 0)\n"
            "            self.assertTrue(p.exists()); self.assertEqual(planned_renames(tmp, 'pre_')[0][1].name, 'pre_a.txt')\n"
            "if __name__ == '__main__': unittest.main()\n"
        ),
    }


def _markdown_table_files() -> dict[str, str]:
    return {
        "README.md": "# live_provider_markdown_table_formatter\n\nRun: `python markdown_table_formatter.py --input sample.csv --output table.md`.\n",
        "sample.csv": "Name,Amount\nCoffee,3.50\nLunch,12.00\n",
        "markdown_table_formatter.py": (
            "from __future__ import annotations\n\nimport argparse, csv\nfrom pathlib import Path\n\n"
            "def csv_to_markdown(path: str) -> str:\n"
            "    rows = list(csv.reader(Path(path).read_text(encoding='utf-8').splitlines()))\n"
            "    widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]\n"
            "    def fmt(row): return '| ' + ' | '.join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)) + ' |'\n"
            "    sep = '| ' + ' | '.join('-' * w for w in widths) + ' |'\n"
            "    return '\\n'.join([fmt(rows[0]), sep, *[fmt(row) for row in rows[1:]]]) + '\\n'\n\n"
            "def main(argv=None):\n"
            "    p = argparse.ArgumentParser(); p.add_argument('--input', required=True); p.add_argument('--output', required=True)\n"
            "    a = p.parse_args(argv); Path(a.output).write_text(csv_to_markdown(a.input), encoding='utf-8'); return 0\n\n"
            "if __name__ == '__main__': raise SystemExit(main())\n"
        ),
        "tests/__init__.py": "# unittest package marker\n",
        "tests/test_markdown_table_formatter.py": (
            "import tempfile, unittest\nfrom pathlib import Path\nfrom markdown_table_formatter import csv_to_markdown, main\n\n"
            "class MarkdownTableFormatterTests(unittest.TestCase):\n"
            "    def test_csv_to_markdown(self):\n"
            "        table = csv_to_markdown('sample.csv')\n"
            "        self.assertIn('Name', table); self.assertIn('Amount', table); self.assertIn('Coffee', table)\n"
            "    def test_cli_writes_output(self):\n"
            "        with tempfile.TemporaryDirectory() as tmp:\n"
            "            out = Path(tmp) / 'table.md'; self.assertEqual(main(['--input', 'sample.csv', '--output', str(out)]), 0); self.assertIn('Coffee', out.read_text())\n"
            "if __name__ == '__main__': unittest.main()\n"
        ),
    }


def _config_validator_files() -> dict[str, str]:
    return {
        "README.md": "# live_provider_json_config_validator\n\nImport `validate_config` from `config_validator`.\n",
        "config_validator/__init__.py": "from .validator import DEFAULT_SCHEMA, explain_errors, load_and_validate, validate_config\n__all__ = ['DEFAULT_SCHEMA', 'validate_config', 'load_and_validate', 'explain_errors']\n",
        "config_validator/validator.py": (
            "from __future__ import annotations\n\nimport json\nfrom pathlib import Path\n\n"
            "DEFAULT_SCHEMA = {'required': {'name': str, 'enabled': bool}, 'defaults': {'retries': 3}}\n\n"
            "def validate_config(config: dict, schema: dict | None = None) -> dict:\n"
            "    active = schema or DEFAULT_SCHEMA; errors = []; result = dict(config or {})\n"
            "    for key, typ in active.get('required', {}).items():\n"
            "        if key not in result: errors.append({'field': key, 'error': 'missing'}); continue\n"
            "        if not isinstance(result[key], typ): errors.append({'field': key, 'error': f'expected_{typ.__name__}'})\n"
            "    for key, value in active.get('defaults', {}).items(): result.setdefault(key, value)\n"
            "    return {'valid': not errors, 'errors': errors, 'config': result}\n\n"
            "def load_and_validate(path: str, schema: dict | None = None) -> dict:\n"
            "    return validate_config(json.loads(Path(path).read_text(encoding='utf-8')), schema)\n\n"
            "def explain_errors(errors: list[dict]) -> str:\n"
            "    return '; '.join(f\"{e.get('field')}: {e.get('error')}\" for e in errors)\n"
        ),
        "tests/__init__.py": "# unittest package marker\n",
        "tests/test_validator.py": (
            "import unittest\nfrom config_validator import explain_errors, validate_config\n\n"
            "class ConfigValidatorTests(unittest.TestCase):\n"
            "    def test_valid_defaults(self):\n"
            "        r = validate_config({'name': 'demo', 'enabled': True}); self.assertTrue(r['valid']); self.assertEqual(r['config']['retries'], 3)\n"
            "    def test_invalid_errors(self):\n"
            "        r = validate_config({'enabled': 'yes'}); self.assertFalse(r['valid']); self.assertIn('name', explain_errors(r['errors']))\n"
            "if __name__ == '__main__': unittest.main()\n"
        ),
    }


def _static_site_files() -> dict[str, str]:
    return {
        "README.md": "# live_provider_static_site_generator\n\nRun: `python site_generator.py --input content --output site`.\n",
        "content/index.txt": "# Home\n\nWelcome to the demo site.\n",
        "site_generator.py": (
            "from __future__ import annotations\n\nimport argparse, html\nfrom pathlib import Path\n\n"
            "def render_text(text: str) -> str:\n"
            "    lines = text.splitlines(); body = []\n"
            "    for line in lines:\n"
            "        if line.startswith('# '): body.append(f'<h1>{html.escape(line[2:])}</h1>')\n"
            "        elif line.strip(): body.append(f'<p>{html.escape(line)}</p>')\n"
            "    return '<html><body>' + '\\n'.join(body) + '</body></html>\\n'\n\n"
            "def build_site(input_dir: str, output_dir: str) -> list[str]:\n"
            "    src = Path(input_dir).resolve(); out = Path(output_dir).resolve(); out.mkdir(parents=True, exist_ok=True); written = []\n"
            "    for item in sorted(src.glob('*.txt')):\n"
            "        target = out / (item.stem + '.html')\n"
            "        if out not in target.resolve().parents: raise ValueError('unsafe output path')\n"
            "        target.write_text(render_text(item.read_text(encoding='utf-8')), encoding='utf-8'); written.append(target.name)\n"
            "    if 'index.html' not in written: (out / 'index.html').write_text('<html><body><h1>Index</h1></body></html>\\n', encoding='utf-8'); written.append('index.html')\n"
            "    return written\n\n"
            "def main(argv=None):\n"
            "    p = argparse.ArgumentParser(); p.add_argument('--input', required=True); p.add_argument('--output', required=True)\n"
            "    a = p.parse_args(argv); build_site(a.input, a.output); return 0\n\n"
            "if __name__ == '__main__': raise SystemExit(main())\n"
        ),
        "tests/__init__.py": "# unittest package marker\n",
        "tests/test_site_generator.py": (
            "import tempfile, unittest\nfrom pathlib import Path\nfrom site_generator import build_site, render_text\n\n"
            "class StaticSiteGeneratorTests(unittest.TestCase):\n"
            "    def test_render(self): self.assertIn('<h1>Hi</h1>', render_text('# Hi'))\n"
            "    def test_build_site(self):\n"
            "        with tempfile.TemporaryDirectory() as tmp:\n"
            "            src = Path(tmp) / 'src'; out = Path(tmp) / 'out'; src.mkdir(); (src / 'index.txt').write_text('# Home')\n"
            "            build_site(str(src), str(out)); self.assertTrue((out / 'index.html').exists())\n"
            "if __name__ == '__main__': unittest.main()\n"
        ),
    }


def blind_candidate_files(project_id: str) -> dict[str, str]:
    builders = {
        "live_provider_unit_converter_cli": _unit_converter_files,
        "live_provider_file_renamer_cli": _file_renamer_files,
        "live_provider_markdown_table_formatter": _markdown_table_files,
        "live_provider_json_config_validator": _config_validator_files,
        "live_provider_static_site_generator": _static_site_files,
    }
    return builders[project_id]()
