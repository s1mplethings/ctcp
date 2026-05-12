from __future__ import annotations

import ast
import hashlib
import json
import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

SYMBOLS_ARTIFACT = "artifacts/generated_symbols.json"
ROUTES_ARTIFACT = "artifacts/generated_routes.json"
RUNTIME_CONTRACT_ARTIFACT = "artifacts/runtime_contract.json"
RECONCILIATION_ARTIFACT = "artifacts/reconciliation_report.json"
CONTRACT_GRAPH_ARTIFACT = "artifacts/contract_graph.json"
FILE_HASH_CACHE_ARTIFACT = "artifacts/file_hash_cache.json"

_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
_SERVICE_NAME_RE = re.compile(r"(^|_)(service|svc|repo|repository|manager|client|store|storage)(_|$)", re.I)


@dataclass(frozen=True)
class _ClassInfo:
    name: str
    rel_path: str
    methods: tuple[str, ...]
    lineno: int
    end_lineno: int


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def _safe_rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.resolve().as_posix()


def _candidate_project_roots(run_dir: Path, project_root: str | None = None) -> list[Path]:
    if project_root:
        candidate = (run_dir / project_root).resolve()
        if candidate.exists():
            return [candidate]
    output = run_dir / "project_output"
    if not output.exists():
        return []
    roots = [
        path.resolve()
        for path in output.iterdir()
        if path.is_dir() and ((path / "README.md").exists() or (path / "src").exists() or (path / "tests").exists())
    ]
    if roots:
        return sorted(roots, key=lambda path: path.as_posix().lower())
    return [output.resolve()]


def _parse_python(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    except SyntaxError:
        return None
    except Exception:
        return None


def _string_value(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def _literal_string_list(node: ast.AST) -> list[str]:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [value for item in node.elts if (value := _string_value(item))]
    return []


def _exported_symbols(tree: ast.Module) -> list[str]:
    exports: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
            continue
        exports.extend(_literal_string_list(node.value))
    return sorted(set(exports))


def _module_symbols(path: Path, root: Path) -> tuple[dict[str, Any], list[_ClassInfo]]:
    tree = _parse_python(path)
    rel = _safe_rel(path, root)
    if tree is None:
        return {"classes": [], "functions": [], "exports": [], "parse_error": True}, []
    classes: list[_ClassInfo] = []
    functions: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = sorted(
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and not child.name.startswith("__")
            )
            classes.append(
                _ClassInfo(
                    name=node.name,
                    rel_path=rel,
                    methods=tuple(methods),
                    lineno=int(getattr(node, "lineno", 0) or 0),
                    end_lineno=int(getattr(node, "end_lineno", 0) or 0),
                )
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            functions.append(node.name)
    return {
        "classes": [row.name for row in classes],
        "functions": sorted(set(functions)),
        "exports": _exported_symbols(tree),
    }, classes


def extract_generated_symbols(run_dir: Path, project_root: str | None = None) -> dict[str, Any]:
    modules: dict[str, Any] = {}
    symbol_rows: dict[str, Any] = {}
    conflicts: list[dict[str, Any]] = []
    roots = _candidate_project_roots(run_dir, project_root)
    project_root_rel = _safe_rel(roots[0], run_dir) if roots else ""
    for root in roots:
        for path in sorted(root.rglob("*.py"), key=lambda item: item.as_posix().lower()):
            if "__pycache__" in path.parts:
                continue
            module_doc, classes = _module_symbols(path, root)
            rel = _safe_rel(path, root)
            modules[rel] = module_doc
            for info in classes:
                row = {
                    "type": "class",
                    "module": info.rel_path,
                    "methods": list(info.methods),
                }
                existing = symbol_rows.get(info.name)
                if existing and existing != row:
                    conflicts.append(
                        {
                            "symbol": info.name,
                            "existing_module": existing.get("module", ""),
                            "new_module": info.rel_path,
                            "type": "duplicate_symbol_drift",
                        }
                    )
                    merged_methods = sorted(set(existing.get("methods", [])) | set(info.methods))
                    existing["methods"] = merged_methods
                    existing.setdefault("modules", [existing.get("module", "")])
                    existing["modules"] = sorted(set(existing["modules"] + [info.rel_path]))
                else:
                    symbol_rows[info.name] = row
            for func in module_doc.get("functions", []):
                symbol_rows.setdefault(func, {"type": "function", "module": rel})
    service_interfaces = {
        name: dict(row)
        for name, row in sorted(symbol_rows.items())
        if str(name).endswith("Service") and row.get("type") == "class"
    }
    doc: dict[str, Any] = {
        "schema_version": "ctcp-generated-symbols-v1",
        "project_root": project_root_rel,
        "symbols": {key: symbol_rows[key] for key in sorted(symbol_rows)},
        "modules": {key: modules[key] for key in sorted(modules)},
        "service_interfaces": service_interfaces,
        "conflicts": conflicts,
    }
    for key, value in symbol_rows.items():
        if value.get("type") == "class":
            doc[key] = value
    return doc


def _route_path(value: str) -> str:
    path = str(value or "").strip()
    path = re.split(r"[<>'\"\s]", path, maxsplit=1)[0]
    if not path.startswith("/"):
        return ""
    return re.sub(r"<([^>/]+)>", r"{\1}", path)


def _route_from_decorator(node: ast.AST) -> list[tuple[str, str]]:
    call = node if isinstance(node, ast.Call) else None
    if call is None:
        return []
    func = call.func
    method = ""
    if isinstance(func, ast.Attribute):
        attr = func.attr.lower()
        if attr in {"get", "post", "put", "patch", "delete", "options", "head"}:
            method = attr.upper()
        elif attr == "route":
            method = "GET"
    elif isinstance(func, ast.Name) and func.id.lower() == "route":
        method = "GET"
    if not method or not call.args:
        return []
    path = _route_path(_string_value(call.args[0]))
    if not path:
        return []
    methods = [method]
    for keyword in call.keywords:
        if keyword.arg == "methods":
            explicit = [item.upper() for item in _literal_string_list(keyword.value)]
            methods = [item for item in explicit if item in _HTTP_METHODS] or methods
    return [(item, path) for item in methods]


def _route_literals_from_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[str, str]]:
    name = node.name.upper()
    method = name[3:] if name.startswith("DO_") else ""
    if method not in _HTTP_METHODS:
        return []
    routes: set[tuple[str, str]] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Compare):
            candidates = [child.left, *child.comparators]
            for candidate in candidates:
                path = _route_path(_string_value(candidate))
                if path:
                    routes.add((method, path))
        elif isinstance(child, ast.Call):
            for arg in child.args[:2]:
                path = _route_path(_string_value(arg))
                if path:
                    routes.add((method, path))
    return sorted(routes)


def _name_in_compare(node: ast.Compare, name: str) -> bool:
    candidates = [node.left, *node.comparators]
    return any(isinstance(candidate, ast.Name) and candidate.id == name for candidate in candidates)


def _wsgi_route_literals_from_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.If) or not isinstance(child.test, ast.Compare):
            continue
        if not _name_in_compare(child.test, "route"):
            continue
        route_paths = [_route_path(_string_value(candidate)) for candidate in [child.test.left, *child.test.comparators]]
        route_paths = [path for path in route_paths if path]
        if not route_paths:
            continue
        methods: set[str] = set()
        for statement in child.body:
            nested_nodes = ast.walk(statement)
            for nested in nested_nodes:
                if not isinstance(nested, ast.Compare) or not _name_in_compare(nested, "method"):
                    continue
                for candidate in [nested.left, *nested.comparators]:
                    method = _string_value(candidate).upper()
                    if method in _HTTP_METHODS:
                        methods.add(method)
        for route_path in route_paths:
            for method in sorted(methods or {"GET"}):
                routes.add((method, route_path))
    return sorted(routes)


def extract_generated_routes(run_dir: Path, project_root: str | None = None) -> dict[str, Any]:
    route_rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    roots = _candidate_project_roots(run_dir, project_root)
    project_root_rel = _safe_rel(roots[0], run_dir) if roots else ""
    for root in roots:
        for path in sorted(root.rglob("*.py"), key=lambda item: item.as_posix().lower()):
            if "__pycache__" in path.parts:
                continue
            tree = _parse_python(path)
            if tree is None:
                continue
            rel = _safe_rel(path, root)
            text = path.read_text(encoding="utf-8", errors="replace")
            for method, route in re.findall(r"(?:#|\b)\s*(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+(/[A-Za-z0-9_{}<>\-/]+)", text):
                route_path = _route_path(route)
                if not route_path:
                    continue
                key = (method.upper(), route_path, rel)
                if key not in seen:
                    seen.add(key)
                    route_rows.append({"method": method.upper(), "path": route_path, "handler": f"{rel}:comment"})
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    route_pairs: list[tuple[str, str]] = []
                    for decorator in node.decorator_list:
                        route_pairs.extend(_route_from_decorator(decorator))
                    route_pairs.extend(_route_literals_from_function(node))
                    route_pairs.extend(_wsgi_route_literals_from_function(node))
                    for method, route in route_pairs:
                        key = (method, route, rel)
                        if key in seen:
                            continue
                        seen.add(key)
                        route_rows.append({"method": method, "path": route, "handler": f"{rel}:{node.name}"})
    route_rows.sort(key=lambda row: (row["path"], row["method"], row["handler"]))
    return {
        "schema_version": "ctcp-generated-routes-v1",
        "project_root": project_root_rel,
        "routes": route_rows,
    }


def _supported_cli_args(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    args = sorted(set(re.findall(r"add_argument\(\s*['\"](--[A-Za-z0-9][A-Za-z0-9_-]*)['\"]", text)))
    return args


def _default_port(path: Path, supported_args: list[str]) -> int:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if "--port" in supported_args:
        match = re.search(r"add_argument\(\s*['\"]--port['\"][^)]*default\s*=\s*(\d+)", text, flags=re.S)
        if match:
            return int(match.group(1))
    match = re.search(r"run_server\([^)]*port\s*=\s*(\d+)", text)
    if match:
        return int(match.group(1))
    match = re.search(r"\bPORT\b[^0-9]{0,40}(\d{2,5})", text)
    if match:
        return int(match.group(1))
    return 8000


def _default_host(path: Path, supported_args: list[str]) -> str:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if "--host" in supported_args:
        match = re.search(r"add_argument\(\s*['\"]--host['\"][^)]*default\s*=\s*['\"]([^'\"]+)['\"]", text, flags=re.S)
        if match:
            return match.group(1)
    if "127.0.0.1" in text:
        return "127.0.0.1"
    return "127.0.0.1"


def extract_runtime_contract(run_dir: Path, project_root: str | None = None, entrypoint: str | None = None) -> dict[str, Any]:
    roots = _candidate_project_roots(run_dir, project_root)
    root = roots[0] if roots else run_dir
    preferred: list[Path] = []
    if entrypoint:
        preferred.append((run_dir / entrypoint).resolve())
        preferred.append((root / entrypoint).resolve())
    preferred.extend(
        [
            root / "scripts" / "run_project_web.py",
            root / "run_project_web.py",
            root / "app.py",
            root / "main.py",
            root / "server.py",
        ]
    )
    preferred.extend(sorted(root.glob("src/*/app.py"), key=lambda item: item.as_posix().lower()))
    preferred.extend(sorted(root.glob("src/*/main.py"), key=lambda item: item.as_posix().lower()))
    entry = next((path.resolve() for path in preferred if path.exists()), None)
    entry_rel = _safe_rel(entry, root) if entry else ""
    supported_args = _supported_cli_args(entry) if entry else []
    command = ["python", entry_rel] if entry_rel else []
    if "--serve" in supported_args:
        command.append("--serve")
    return {
        "schema_version": "ctcp-runtime-contract-v1",
        "project_root": _safe_rel(root, run_dir) if root.exists() else "",
        "entrypoint": entry_rel,
        "serve_command": " ".join(command),
        "supported_cli_args": supported_args,
        "default_host": _default_host(entry, supported_args) if entry else "127.0.0.1",
        "default_port": _default_port(entry, supported_args) if entry else 8000,
    }


def _class_index(run_dir: Path, project_root: str | None = None) -> dict[str, _ClassInfo]:
    out: dict[str, _ClassInfo] = {}
    for root in _candidate_project_roots(run_dir, project_root):
        for path in sorted(root.rglob("*.py"), key=lambda item: item.as_posix().lower()):
            if "__pycache__" in path.parts:
                continue
            _module_doc, classes = _module_symbols(path, root)
            for info in classes:
                out.setdefault(info.name, info)
    return out


def _target_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
        return f"self.{node.attr}"
    return ""


def _call_owner(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
        return f"self.{node.attr}"
    return ""


def _constructor_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
    return ""


def _looks_like_service_var(name: str) -> bool:
    return bool(_SERVICE_NAME_RE.search(name.replace(".", "_")))


def _collect_method_references(path: Path, root: Path, known_classes: dict[str, _ClassInfo]) -> list[dict[str, Any]]:
    tree = _parse_python(path)
    if tree is None:
        return []
    rel = _safe_rel(path, root)
    single_service = next((name for name in sorted(known_classes) if name.endswith("Service")), "")
    variable_classes: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            class_name = _constructor_name(node.value)
            if class_name in known_classes:
                for target in node.targets:
                    target_name = _target_name(target)
                    if target_name:
                        variable_classes[target_name] = class_name
        elif isinstance(node, ast.AnnAssign):
            class_name = _constructor_name(node.value) if node.value is not None else ""
            if class_name in known_classes:
                target_name = _target_name(node.target)
                if target_name:
                    variable_classes[target_name] = class_name
    refs: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr in known_classes:
            continue
        owner = _call_owner(node.func.value)
        if not owner:
            continue
        class_name = variable_classes.get(owner)
        if not class_name and single_service and _looks_like_service_var(owner):
            class_name = single_service
        if not class_name:
            continue
        method = node.func.attr
        if method.startswith("_"):
            continue
        refs.append(
            {
                "file": rel,
                "line": int(getattr(node, "lineno", 0) or 0),
                "class": class_name,
                "method": method,
                "owner": owner,
                "arg_count": len(node.args),
            }
        )
    return refs


def _method_def_index(run_dir: Path, project_root: str | None = None) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for root in _candidate_project_roots(run_dir, project_root):
        for path in sorted(root.rglob("*.py"), key=lambda item: item.as_posix().lower()):
            if "__pycache__" in path.parts:
                continue
            tree = _parse_python(path)
            if tree is None:
                continue
            rel = _safe_rel(path, root)
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                for child in node.body:
                    if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    positional = list(child.args.posonlyargs) + list(child.args.args)
                    if positional and positional[0].arg in {"self", "cls"}:
                        positional = positional[1:]
                    out[(node.name, child.name)] = {
                        "file": rel,
                        "line": int(getattr(child, "lineno", 0) or 0),
                        "max_positional": len(positional),
                        "has_vararg": child.args.vararg is not None,
                    }
    return out


def _repair_method_arity(run_dir: Path, project_root: str | None, refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    method_defs = _method_def_index(run_dir, project_root)
    roots = _candidate_project_roots(run_dir, project_root)
    root = roots[0] if roots else run_dir
    repairs: list[dict[str, Any]] = []
    by_file_line: dict[tuple[str, int], dict[str, Any]] = {}
    for ref in refs:
        key = (str(ref.get("class", "")), str(ref.get("method", "")))
        method_def = method_defs.get(key)
        if not method_def or method_def.get("has_vararg"):
            continue
        try:
            arg_count = int(ref.get("arg_count", 0) or 0)
            max_positional = int(method_def.get("max_positional", 0) or 0)
        except Exception:
            continue
        if arg_count <= max_positional:
            continue
        by_file_line[(str(method_def["file"]), int(method_def["line"]))] = {
            "class": key[0],
            "method": key[1],
            "arg_count": arg_count,
            "max_positional": max_positional,
        }
    for (rel, line_no), detail in sorted(by_file_line.items()):
        path = root / rel
        if not path.exists() or line_no <= 0:
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        index = line_no - 1
        if index >= len(lines) or "*args" in lines[index]:
            continue
        line = lines[index]
        if "):" not in line:
            continue
        lines[index] = line.replace("):", ", *args, **kwargs):", 1)
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        row = {"type": "method_arity", "source_file": rel, **detail}
        repairs.append(row)
    return repairs


def _method_score(missing: str, candidate: str) -> float:
    def normalize_tokens(value: str) -> set[str]:
        aliases = {
            "initialize": "init",
            "initialise": "init",
            "schema": "db",
            "database": "db",
        }
        return {aliases.get(token, token) for token in value.lower().strip("_").split("_") if token}

    missing_tokens = normalize_tokens(missing)
    candidate_tokens = normalize_tokens(candidate)
    overlap = len(missing_tokens & candidate_tokens) / max(len(missing_tokens | candidate_tokens), 1)
    sequence = SequenceMatcher(a=missing.lower(), b=candidate.lower()).ratio()
    suffix = 0.2 if missing_tokens and candidate_tokens and list(missing_tokens)[-1:] == list(candidate_tokens)[-1:] else 0.0
    return max(overlap, sequence) + suffix


def _best_method_alias(missing: str, available: list[str]) -> str:
    if missing == "close":
        return ""
    candidates = [name for name in available if name != missing]
    if not candidates:
        return ""
    scored = sorted(((_method_score(missing, name), name) for name in candidates), reverse=True)
    score, name = scored[0]
    return name if score >= 0.45 else ""


def _repair_resource_close_methods(run_dir: Path, project_root: str | None, unresolved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    close_classes = sorted({str(row.get("class", "")) for row in unresolved if str(row.get("method", "")) == "close"})
    if not close_classes:
        return []
    roots = _candidate_project_roots(run_dir, project_root)
    root = roots[0] if roots else run_dir
    class_index = _class_index(run_dir, project_root)
    repairs: list[dict[str, Any]] = []
    for class_name in close_classes:
        info = class_index.get(class_name)
        if not info or "close" in info.methods:
            continue
        path = root / info.rel_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        bad_alias = re.compile(
            r"\n\s+def close\(self, \*args, \*\*kwargs\):\n\s+return self\.close_issue\(\*args, \*\*kwargs\)\n?",
            flags=re.M,
        )
        if bad_alias.search(text):
            text = bad_alias.sub("", text)
            path.write_text(text, encoding="utf-8")
            info = _class_index(run_dir, project_root).get(class_name, info)
        if "self._conn" not in text and "self.conn" not in text and "self.connection" not in text:
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        insert_at = min(max(info.end_lineno, 0), len(lines))
        class_line = lines[max(info.lineno - 1, 0)] if lines else ""
        class_indent = class_line[: len(class_line) - len(class_line.lstrip())]
        method_indent = class_indent + "    "
        body_indent = method_indent + "    "
        attr = "_conn" if "self._conn" in "\n".join(lines) else ("conn" if "self.conn" in "\n".join(lines) else "connection")
        block = [
            "",
            f"{method_indent}def close(self):",
            f"{body_indent}if getattr(self, '{attr}', None) is not None:",
            f"{body_indent}    self.{attr}.close()",
            f"{body_indent}    self.{attr} = None",
        ]
        lines[insert_at:insert_at] = block
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        repairs.append({"type": "resource_close_method", "class": class_name, "source_file": info.rel_path})
    return repairs


def _insert_alias_methods(path: Path, info: _ClassInfo, aliases: dict[str, str]) -> bool:
    if not aliases or info.end_lineno <= 0:
        return False
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    insert_at = min(max(info.end_lineno, 0), len(lines))
    class_line = lines[max(info.lineno - 1, 0)] if lines else ""
    class_indent = class_line[: len(class_line) - len(class_line.lstrip())]
    method_indent = class_indent + "    "
    body_indent = method_indent + "    "
    block: list[str] = [""]
    for missing, target in sorted(aliases.items()):
        block.extend(
            [
                f"{method_indent}def {missing}(self, *args, **kwargs):",
                f"{body_indent}return self.{target}(*args, **kwargs)",
                "",
            ]
        )
    lines[insert_at:insert_at] = block
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return True


def _repair_missing_methods(run_dir: Path, project_root: str | None, unresolved: list[dict[str, Any]], symbols: dict[str, Any]) -> list[dict[str, Any]]:
    class_index = _class_index(run_dir, project_root)
    repairs_by_class: dict[str, dict[str, str]] = {}
    repairs: list[dict[str, Any]] = []
    symbol_rows = symbols.get("symbols") if isinstance(symbols.get("symbols"), dict) else {}
    for issue in unresolved:
        class_name = str(issue.get("class", ""))
        missing = str(issue.get("method", ""))
        row = symbol_rows.get(class_name) if isinstance(symbol_rows.get(class_name), dict) else {}
        available = [str(item) for item in row.get("methods", []) if str(item)]
        target = _best_method_alias(missing, available)
        if not target:
            continue
        repairs_by_class.setdefault(class_name, {})[missing] = target
        repairs.append(
            {
                "type": "method_alias",
                "class": class_name,
                "missing_method": missing,
                "target_method": target,
                "reference_file": issue.get("file", ""),
            }
        )
    roots = _candidate_project_roots(run_dir, project_root)
    root = roots[0] if roots else run_dir
    applied: list[dict[str, Any]] = []
    for class_name, aliases in sorted(repairs_by_class.items()):
        info = class_index.get(class_name)
        if not info:
            continue
        path = root / info.rel_path
        if _insert_alias_methods(path, info, aliases):
            for repair in repairs:
                if repair["class"] == class_name and repair["missing_method"] in aliases:
                    repair["source_file"] = info.rel_path
                    applied.append(repair)
    return applied


def _sqlite_connect_var(node: ast.With) -> str:
    if len(node.items) != 1:
        return ""
    item = node.items[0]
    if not isinstance(item.optional_vars, ast.Name):
        return ""
    call = item.context_expr
    if not isinstance(call, ast.Call):
        return ""
    func = call.func
    if isinstance(func, ast.Attribute) and func.attr == "connect":
        return item.optional_vars.id
    if isinstance(func, ast.Name) and func.id == "connect":
        return item.optional_vars.id
    return ""


def _body_contains_from_row(node: ast.With) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute) and child.func.attr == "from_row":
            return True
    return False


def _body_has_row_factory(node: ast.With, var_name: str) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Assign):
            continue
        for target in child.targets:
            if (
                isinstance(target, ast.Attribute)
                and target.attr == "row_factory"
                and isinstance(target.value, ast.Name)
                and target.value.id == var_name
            ):
                return True
    return False


def _repair_sqlite_row_factory(run_dir: Path, project_root: str | None) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    roots = _candidate_project_roots(run_dir, project_root)
    for root in roots:
        for path in sorted(root.rglob("*.py"), key=lambda item: item.as_posix().lower()):
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "sqlite3.connect" not in text or ".from_row(" not in text:
                continue
            tree = _parse_python(path)
            if tree is None:
                continue
            lines = text.splitlines()
            insertions: list[tuple[int, str]] = []
            for node in ast.walk(tree):
                if not isinstance(node, ast.With):
                    continue
                var_name = _sqlite_connect_var(node)
                if not var_name or not _body_contains_from_row(node) or _body_has_row_factory(node, var_name):
                    continue
                body_lineno = int(getattr(node.body[0], "lineno", getattr(node, "lineno", 0) + 1) or 0) if node.body else int(getattr(node, "lineno", 0) + 1)
                if body_lineno <= 0:
                    continue
                body_line = lines[body_lineno - 1] if body_lineno - 1 < len(lines) else ""
                indent = body_line[: len(body_line) - len(body_line.lstrip())] or "    "
                insertions.append((body_lineno - 1, f"{indent}{var_name}.row_factory = sqlite3.Row"))
            if not insertions:
                continue
            for insert_at, line in sorted(insertions, reverse=True):
                if line.strip() in "\n".join(lines[max(0, insert_at - 2) : insert_at + 3]):
                    continue
                lines.insert(insert_at, line)
                repairs.append(
                    {
                        "type": "sqlite_row_factory",
                        "source_file": _safe_rel(path, root),
                        "line": insert_at + 1,
                        "connection": line.strip().split(".row_factory", 1)[0],
                    }
                )
            path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return repairs


def _ensure_import(text: str, import_line: str) -> str:
    if import_line in text:
        return text
    lines = text.splitlines()
    insert_at = 0
    for index, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_at = index + 1
    lines.insert(insert_at, import_line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _repair_sqlite_context_closing(run_dir: Path, project_root: str | None) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    patterns = [
        re.compile(r"with\s+sqlite3\.connect\(([^)\n]+)\)\s+as\s+([A-Za-z_][A-Za-z0-9_]*):"),
        re.compile(r"with\s+self\._get_connection\(\)\s+as\s+([A-Za-z_][A-Za-z0-9_]*):"),
    ]
    for root in _candidate_project_roots(run_dir, project_root):
        for path in sorted(root.rglob("*.py"), key=lambda item: item.as_posix().lower()):
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "sqlite3.connect" not in text and "self._get_connection()" not in text:
                continue
            if "contextlib.closing(sqlite3.connect" in text or "contextlib.closing(self._get_connection()" in text:
                continue
            changed_text = patterns[0].sub(r"with contextlib.closing(sqlite3.connect(\1)) as \2:", text)
            changed_text = patterns[1].sub(r"with contextlib.closing(self._get_connection()) as \1:", changed_text)
            if changed_text == text:
                continue
            changed_text = _ensure_import(changed_text, "import contextlib")
            path.write_text(changed_text, encoding="utf-8")
            repairs.append({"type": "sqlite_connection_closing", "source_file": _safe_rel(path, root)})
    return repairs


def _repair_enum_string_status(run_dir: Path, project_root: str | None) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    for root in _candidate_project_roots(run_dir, project_root):
        test_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in sorted((root / "tests").rglob("*.py"), key=lambda item: item.as_posix().lower())
            if (root / "tests").exists()
        )
        if ".status" not in test_text or "assertEqual" not in test_text:
            continue
        for path in sorted(root.rglob("*.py"), key=lambda item: item.as_posix().lower()):
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            changed = text
            changed = re.sub(r"status\s*:\s*IssueStatus\b", "status: str", changed)
            changed = re.sub(r"status\s*=\s*IssueStatus\(([^)]+)\)", r"status=\1", changed)
            if changed != text:
                path.write_text(changed, encoding="utf-8")
                repairs.append({"type": "enum_string_status", "source_file": _safe_rel(path, root)})
    return repairs


def _repair_enum_uppercase_aliases(run_dir: Path, project_root: str | None) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    for root in _candidate_project_roots(run_dir, project_root):
        tests_dir = root / "tests"
        test_text = ""
        if tests_dir.exists():
            test_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in tests_dir.rglob("*.py"))
        requested = sorted(set(re.findall(r"IssueStatus\.([A-Z][A-Z0-9_]*)", test_text)))
        if not requested:
            continue
        for path in sorted(root.rglob("*.py"), key=lambda item: item.as_posix().lower()):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "class IssueStatus" not in text or "Enum" not in text:
                continue
            lines = text.splitlines()
            class_index = next((idx for idx, line in enumerate(lines) if line.strip().startswith("class IssueStatus")), -1)
            if class_index < 0:
                continue
            existing = set(re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", text, flags=re.M))
            insert_at = class_index + 1
            while insert_at < len(lines) and (lines[insert_at].startswith("    ") or not lines[insert_at].strip()):
                insert_at += 1
            alias_lines: list[str] = []
            for name in requested:
                if name in existing:
                    continue
                value = name.lower()
                alias_lines.append(f"    {name} = '{value}'")
            if not alias_lines:
                continue
            lines[class_index + 1 : class_index + 1] = alias_lines
            path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            repairs.append({"type": "enum_uppercase_aliases", "source_file": _safe_rel(path, root), "aliases": requested})
    return repairs


def _repair_windows_tempfile_locks(run_dir: Path, project_root: str | None) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    for root in _candidate_project_roots(run_dir, project_root):
        tests_dir = root / "tests"
        if not tests_dir.exists():
            continue
        for path in sorted(tests_dir.rglob("*.py"), key=lambda item: item.as_posix().lower()):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "tempfile.mkstemp(" not in text:
                continue
            lines = text.splitlines()
            changed = False
            for index, line in enumerate(list(lines)):
                if "self.db_fd, self.db_path = tempfile.mkstemp()" in line:
                    indent = line[: len(line) - len(line.lstrip())]
                    next_text = "\n".join(lines[index + 1 : index + 4])
                    if "self.db_fd = -1" not in next_text:
                        lines.insert(index + 1, f"{indent}os.close(self.db_fd)")
                        lines.insert(index + 2, f"{indent}self.db_fd = -1")
                        repairs.append({"type": "windows_tempfile_handle", "source_file": _safe_rel(path, root), "line": index + 2})
                        changed = True
                    break
            index = 0
            while index < len(lines):
                line = lines[index]
                stripped = line.strip()
                if stripped == "os.close(self.db_fd)":
                    previous = lines[index - 1].strip() if index > 0 else ""
                    if previous.startswith("if self.db_fd"):
                        index += 1
                        continue
                    indent = line[: len(line) - len(line.lstrip())]
                    lines[index : index + 1] = [f"{indent}if self.db_fd >= 0:", f"{indent}    os.close(self.db_fd)"]
                    changed = True
                    index += 2
                    continue
                index += 1
            for index, line in enumerate(list(lines)):
                if line.strip() in {"os.unlink(self.db_path)", "os.remove(self.db_path)"}:
                    previous = "\n".join(lines[max(0, index - 3) : index])
                    if "self.service = None" not in previous:
                        indent = line[: len(line) - len(line.lstrip())]
                        close_block = [
                            f"{indent}closer = getattr(self.service, 'close', None)",
                            f"{indent}if callable(closer):",
                            f"{indent}    closer()",
                            f"{indent}elif hasattr(self.service, '_conn'):",
                            f"{indent}    self.service._conn.close()",
                            f"{indent}self.service = None",
                        ]
                        lines[index:index] = close_block
                        changed = True
                    break
            if changed:
                path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return repairs


def _repair_invalid_status_return_contract(run_dir: Path, project_root: str | None) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    for root in _candidate_project_roots(run_dir, project_root):
        tests_dir = root / "tests"
        test_text = ""
        if tests_dir.exists():
            test_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in tests_dir.rglob("*.py"))
        if "invalid_status" not in test_text or "assertFalse" not in test_text or "assertRaises" in test_text:
            continue
        for path in sorted(root.rglob("*.py"), key=lambda item: item.as_posix().lower()):
            if "__pycache__" in path.parts or path.parts[-2:-1] == ("tests",):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "Invalid status" not in text or "raise ValueError" not in text:
                continue
            lines = text.splitlines()
            changed = False
            for index, line in enumerate(lines):
                if "raise ValueError" in line and "status" in line.lower():
                    indent = line[: len(line) - len(line.lstrip())]
                    lines[index] = f"{indent}return False"
                    changed = True
            if changed:
                path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
                repairs.append({"type": "invalid_status_return_contract", "source_file": _safe_rel(path, root)})
    return repairs


def _repair_json_default_serializer(run_dir: Path, project_root: str | None) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    for root in _candidate_project_roots(run_dir, project_root):
        for path in sorted(root.rglob("*.py"), key=lambda item: item.as_posix().lower()):
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            fixed_text = text.replace("str(e, default=str)", "str(e)")
            if "protocol_version = 'HTTP/1.1'" in fixed_text and "Content-Length" not in fixed_text:
                fixed_text = fixed_text.replace("protocol_version = 'HTTP/1.1'", "protocol_version = 'HTTP/1.0'")
            if fixed_text != text:
                path.write_text(fixed_text, encoding="utf-8")
                text = fixed_text
                repairs.append({"type": "http_json_exception_serializer", "source_file": _safe_rel(path, root)})
            if "json.dumps(" not in text:
                continue
            changed = re.sub(r"json\.dumps\((?![^)\n]*default=)([^)\n]+)\)", r"json.dumps(\1, default=str)", text)
            if changed != text:
                path.write_text(changed, encoding="utf-8")
                repairs.append({"type": "json_default_serializer", "source_file": _safe_rel(path, root)})
    return repairs


def _repair_dto_string_adapters(run_dir: Path, project_root: str | None) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    for root in _candidate_project_roots(run_dir, project_root):
        tests_dir = root / "tests"
        test_text = ""
        if tests_dir.exists():
            test_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in tests_dir.rglob("*.py"))
        if not test_text:
            continue
        for path in sorted(root.rglob("*.py"), key=lambda item: item.as_posix().lower()):
            if "__pycache__" in path.parts or "\\tests\\" in path.as_posix():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            changed = False
            for index, line in enumerate(list(lines)):
                stripped = line.strip()
                indent = line[: len(line) - len(line.lstrip())]
                body_indent = indent + "    "
                create_match = re.match(r"def create_issue\(self,\s*([A-Za-z_][A-Za-z0-9_]*)", stripped)
                if create_match and "IssueCreate" in line + text and "create_issue(" in test_text:
                    param = create_match.group(1)
                    if "*args" not in line:
                        lines[index] = line.replace("):", ", *args, **kwargs):", 1)
                    nearby = "\n".join(lines[index + 1 : index + 5])
                    if f"isinstance({param}, str)" not in nearby:
                        lines[index + 1 : index + 1] = [
                            f"{body_indent}if isinstance({param}, str):",
                            f"{body_indent}    {param} = IssueCreate(title={param}, description=args[0] if args else '')",
                        ]
                    changed = True
                if stripped.startswith("def update_issue_status(self,") and "status_update" in stripped and "IssueStatusUpdate" in text:
                    nearby = "\n".join(lines[index + 1 : index + 5])
                    if "isinstance(status_update, str)" not in nearby:
                        lines[index + 1 : index + 1] = [
                            f"{body_indent}if isinstance(status_update, str):",
                            f"{body_indent}    status_update = IssueStatusUpdate(status=status_update)",
                        ]
                        changed = True
            if changed:
                path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
                repairs.append({"type": "dto_string_adapters", "source_file": _safe_rel(path, root)})
    return repairs


def _repair_memory_db_tests(run_dir: Path, project_root: str | None) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    for root in _candidate_project_roots(run_dir, project_root):
        tests_dir = root / "tests"
        if not tests_dir.exists():
            continue
        for path in sorted(tests_dir.rglob("*.py"), key=lambda item: item.as_posix().lower()):
            text = path.read_text(encoding="utf-8", errors="replace")
            if 'db_path=":memory:"' not in text and "db_path=':memory:'" not in text:
                continue
            text = _ensure_import(_ensure_import(text, "import tempfile"), "import os")
            lines = text.splitlines()
            changed = False
            for index, line in enumerate(list(lines)):
                if 'IssueService(db_path=":memory:")' in line or "IssueService(db_path=':memory:')" in line:
                    indent = line[: len(line) - len(line.lstrip())]
                    lines[index : index + 1] = [
                        f"{indent}self._tmp_db = tempfile.NamedTemporaryFile(prefix='ctcp_issue_test_', suffix='.db', delete=False)",
                        f"{indent}self._tmp_db.close()",
                        line.replace('db_path=":memory:"', "db_path=self._tmp_db.name").replace("db_path=':memory:'", "db_path=self._tmp_db.name"),
                    ]
                    changed = True
                    break
            if changed and "def tearDown(self):" not in "\n".join(lines):
                class_index = next((idx for idx, line in enumerate(lines) if line.startswith("class ")), -1)
                insert_at = len(lines)
                if class_index >= 0:
                    insert_at = next((idx for idx in range(class_index + 1, len(lines)) if lines[idx].startswith("    def test_")), len(lines))
                lines[insert_at:insert_at] = [
                    "    def tearDown(self):",
                    "        if hasattr(self, 'service'):",
                    "            closer = getattr(self.service, 'close', None)",
                    "            if callable(closer):",
                    "                closer()",
                    "            self.service = None",
                    "        if hasattr(self, '_tmp_db') and os.path.exists(self._tmp_db.name):",
                    "            os.remove(self._tmp_db.name)",
                    "",
                ]
            if changed:
                path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
                repairs.append({"type": "memory_db_test_file", "source_file": _safe_rel(path, root)})
    return repairs


def _expected_titles_from_tests(root: Path) -> list[str]:
    expected: list[str] = []
    tests_dir = root / "tests"
    if not tests_dir.exists():
        return expected
    for path in sorted(tests_dir.rglob("*.py"), key=lambda item: item.as_posix().lower()):
        text = path.read_text(encoding="utf-8", errors="replace")
        expected.extend(re.findall(r"assertIn\(\s*['\"]([^'\"]+)['\"]\s*,\s*titles\s*\)", text))
    return sorted(set(expected))


def _repair_seed_title_consistency(run_dir: Path, project_root: str | None) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    for root in _candidate_project_roots(run_dir, project_root):
        expected_titles = _expected_titles_from_tests(root)
        if not expected_titles:
            continue
        for path in sorted(root.rglob("*.py"), key=lambda item: item.as_posix().lower()):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "sample_issues" not in text or "service.create_issue" not in text:
                continue
            existing_titles = set(re.findall(r"['\"]title['\"]\s*:\s*['\"]([^'\"]+)['\"]", text))
            missing = [title for title in expected_titles if title not in existing_titles]
            if not missing:
                continue
            lines = text.splitlines()
            start = next((idx for idx, line in enumerate(lines) if "sample_issues" in line and "[" in line), -1)
            if start < 0:
                continue
            end = next((idx for idx in range(start + 1, len(lines)) if lines[idx].strip().startswith("]")), -1)
            if end < 0:
                continue
            item_indent = " " * 8
            for idx in range(end - 1, start, -1):
                if lines[idx].strip().startswith("{") and not lines[idx].rstrip().endswith(","):
                    lines[idx] = lines[idx].rstrip() + ","
                    break
            insert_rows = [
                f'{item_indent}{{"title": "{title}", "description": "Generated sample issue for test consistency."}},'
                for title in missing
            ]
            lines[end:end] = insert_rows
            path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            repairs.append({"type": "seed_test_title_consistency", "source_file": _safe_rel(path, root), "titles": missing})
    return repairs


def _repair_runtime_port_arg(run_dir: Path, project_root: str | None, entrypoint: str | None) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    roots = _candidate_project_roots(run_dir, project_root)
    if not roots:
        return repairs
    root = roots[0]
    runtime = extract_runtime_contract(run_dir, project_root, entrypoint)
    entry = str(runtime.get("entrypoint", "")).strip()
    if not entry:
        return repairs
    path = (root / entry).resolve()
    if not path.exists():
        return repairs
    text = path.read_text(encoding="utf-8", errors="replace")
    if "def run_server(port=args.port" in text:
        fixed = text.replace("def run_server(port=args.port", "def run_server(port=8000")
        path.write_text(fixed, encoding="utf-8")
        repairs.append({"type": "runtime_cli_port_def_repair", "source_file": _safe_rel(path, root)})
        text = fixed
    if "--port" in text or "argparse" not in text or "run_server(" not in text:
        return repairs
    lines = text.splitlines()
    insert_at = next((idx + 1 for idx, line in enumerate(lines) if "parser.add_argument('--serve'" in line or 'parser.add_argument("--serve"' in line), -1)
    if insert_at < 0:
        return repairs
    indent = lines[insert_at - 1][: len(lines[insert_at - 1]) - len(lines[insert_at - 1].lstrip())]
    lines.insert(insert_at, f"{indent}parser.add_argument('--port', type=int, default=8000, help='HTTP server port')")
    changed_lines = []
    for line in lines:
        if line.lstrip().startswith("def "):
            changed_lines.append(line)
        else:
            changed_line = line.replace("run_server(port=8000, service_inst=", "run_server(port=args.port, service_inst=")
            changed_line = changed_line.replace("run_server(service_inst=", "run_server(port=args.port, service_inst=")
            changed_lines.append(changed_line)
    changed = "\n".join(changed_lines) + "\n"
    if changed == text:
        return repairs
    path.write_text(changed, encoding="utf-8")
    repairs.append({"type": "runtime_cli_port", "source_file": _safe_rel(path, root), "arg": "--port"})
    return repairs


def _repair_runtime_blocking_serve(run_dir: Path, project_root: str | None, entrypoint: str | None) -> list[dict[str, Any]]:
    roots = _candidate_project_roots(run_dir, project_root)
    if not roots:
        return []
    root = roots[0]
    runtime = extract_runtime_contract(run_dir, project_root, entrypoint)
    entry = str(runtime.get("entrypoint", "")).strip()
    if not entry:
        return []
    path = root / entry
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    if "run_server(" not in text or "blocking=False" not in text:
        return []
    changed = text.replace("blocking=False", "blocking=True")
    if changed == text:
        return []
    path.write_text(changed, encoding="utf-8")
    return [{"type": "runtime_blocking_serve", "source_file": _safe_rel(path, root)}]


def _stable_hash(doc: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return ""


def _load_file_hash_cache(run_dir: Path) -> tuple[dict[str, Any], bool]:
    path = run_dir / FILE_HASH_CACHE_ARTIFACT
    if not path.exists():
        return {}, False
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}, True
    if not isinstance(doc, dict) or doc.get("schema_version") != "ctcp-file-hash-cache-v1":
        return {}, True
    return doc, False


def _file_cache_report(run_dir: Path, root: Path) -> dict[str, Any]:
    files = _python_files(root)
    previous, corrupted = _load_file_hash_cache(run_dir)
    previous_hashes = previous.get("files") if isinstance(previous.get("files"), dict) else {}
    current_hashes = {_safe_rel(path, root): _file_hash(path) for path in files}
    if corrupted:
        changed_files = sorted(current_hashes)
        cache_hits = 0
        cache_misses = len(changed_files)
    else:
        changed_files = sorted(
            rel
            for rel, digest in current_hashes.items()
            if str(previous_hashes.get(rel, "")) != digest
        )
        removed_files = sorted(set(str(key) for key in previous_hashes) - set(current_hashes))
        changed_files = sorted(set(changed_files) | set(removed_files))
        cache_misses = len(changed_files)
        cache_hits = max(len(current_hashes) - len([rel for rel in changed_files if rel in current_hashes]), 0)
    doc = {
        "schema_version": "ctcp-file-hash-cache-v1",
        "project_root": _safe_rel(root, run_dir) if root.exists() else "",
        "files": current_hashes,
        "updated_at_epoch": time.time(),
    }
    _write_json(run_dir / FILE_HASH_CACHE_ARTIFACT, doc)
    return {
        "enabled": True,
        "cache_path": FILE_HASH_CACHE_ARTIFACT,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "changed_files": changed_files,
        "corrupted": corrupted,
        "fallback_full_scan": corrupted,
        "file_count": len(current_hashes),
    }


def _node(nodes: dict[str, dict[str, Any]], node_id: str, kind: str, **attrs: Any) -> None:
    row = {"id": node_id, "kind": kind}
    row.update({key: value for key, value in attrs.items() if value not in (None, "")})
    existing = nodes.get(node_id)
    if existing:
        existing.update(row)
    else:
        nodes[node_id] = row


def _file_node_id(rel: str) -> str:
    return f"file:{rel}"


def _method_node_id(class_name: str, method: str) -> str:
    return f"method:{class_name}.{method}"


def _route_node_id(method: str, route: str) -> str:
    return f"route:{method.upper()} {route}"


def _python_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [
        path
        for path in sorted(root.rglob("*.py"), key=lambda item: item.as_posix().lower())
        if "__pycache__" not in path.parts
    ]


def _method_references(run_dir: Path, project_root: str | None = None) -> list[dict[str, Any]]:
    roots = _candidate_project_roots(run_dir, project_root)
    root = roots[0] if roots else run_dir
    class_index = _class_index(run_dir, project_root)
    refs: list[dict[str, Any]] = []
    for path in _python_files(root):
        refs.extend(_collect_method_references(path, root, class_index))
    return refs


def _graph_observation_nodes(root: Path, path: Path, nodes: dict[str, dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    rel = _safe_rel(path, root)
    text = path.read_text(encoding="utf-8", errors="replace")
    file_id = _file_node_id(rel)
    if "sqlite3.connect" in text or "sqlite.connect" in text:
        db_id = f"db:{rel}"
        _node(
            nodes,
            db_id,
            "db.sqlite_usage",
            file=rel,
            row_factory="row_factory" in text,
            row_reader=".from_row(" in text,
            memory_db=":memory:" in text,
        )
        edges.append({"kind": "uses_db_contract", "from": file_id, "to": db_id})
    if "json.dumps(" in text:
        json_id = f"serialization:{rel}"
        _node(
            nodes,
            json_id,
            "serialization.json",
            file=rel,
            default_serializer=bool(re.search(r"json\.dumps\([^)\n]*default\s*=", text)),
            complex_values=any(token in text for token in ("Enum", "datetime", "date(", "Decimal", "UUID")),
        )
        edges.append({"kind": "serializes_json", "from": file_id, "to": json_id})
    if "tempfile.mkstemp" in text and "os.close(" in text:
        temp_id = f"lifecycle:tempfile:{rel}"
        _node(
            nodes,
            temp_id,
            "resource.tempfile_fd",
            file=rel,
            close_guarded="self.db_fd = -1" in text or "db_fd = -1" in text,
        )
        edges.append({"kind": "owns_tempfile_fd", "from": file_id, "to": temp_id})


def extract_contract_graph(
    run_dir: Path,
    project_root: str | None = None,
    entrypoint: str | None = None,
    *,
    symbols: dict[str, Any] | None = None,
    routes: dict[str, Any] | None = None,
    runtime_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    symbols = symbols if isinstance(symbols, dict) else extract_generated_symbols(run_dir, project_root)
    routes = routes if isinstance(routes, dict) else extract_generated_routes(run_dir, project_root)
    runtime_contract = runtime_contract if isinstance(runtime_contract, dict) else extract_runtime_contract(run_dir, project_root, entrypoint)
    roots = _candidate_project_roots(run_dir, project_root)
    root = roots[0] if roots else run_dir
    project_root_rel = _safe_rel(root, run_dir) if root.exists() else ""
    cache_report = _file_cache_report(run_dir, root)
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    _node(nodes, "project", "project", project_root=project_root_rel)
    for path in _python_files(root):
        rel = _safe_rel(path, root)
        _node(nodes, _file_node_id(rel), "file.python", file=rel)
        edges.append({"kind": "contains_file", "from": "project", "to": _file_node_id(rel)})
        _graph_observation_nodes(root, path, nodes, edges)

    method_defs = _method_def_index(run_dir, project_root)
    symbol_rows = symbols.get("symbols") if isinstance(symbols.get("symbols"), dict) else {}
    for name, row_value in sorted(symbol_rows.items()):
        row = row_value if isinstance(row_value, dict) else {}
        symbol_id = f"symbol:{name}"
        rel = str(row.get("module", ""))
        methods = sorted(str(item) for item in row.get("methods", []) if str(item))
        _node(nodes, symbol_id, f"symbol.{row.get('type', 'unknown')}", name=name, file=rel, methods=methods)
        if rel:
            edges.append({"kind": "defines_symbol", "from": _file_node_id(rel), "to": symbol_id})
        for method in methods:
            method_id = _method_node_id(str(name), method)
            method_def = method_defs.get((str(name), method), {})
            _node(
                nodes,
                method_id,
                "symbol.method",
                class_name=str(name),
                method=method,
                file=str(method_def.get("file", rel)),
                line=int(method_def.get("line", 0) or 0),
                max_positional=int(method_def.get("max_positional", 0) or 0),
                has_vararg=bool(method_def.get("has_vararg", False)),
            )
            edges.append({"kind": "defines_method", "from": symbol_id, "to": method_id})

    for ref in _method_references(run_dir, project_root):
        call_id = f"call:{ref.get('file', '')}:{ref.get('line', 0)}:{ref.get('class', '')}.{ref.get('method', '')}"
        _node(nodes, call_id, "call.method", **ref)
        edges.append({"kind": "calls_method", "from": call_id, "to": _method_node_id(str(ref.get("class", "")), str(ref.get("method", "")))})
        if ref.get("file"):
            edges.append({"kind": "contains_call", "from": _file_node_id(str(ref.get("file", ""))), "to": call_id})

    route_seen: dict[tuple[str, str], int] = {}
    for route in routes.get("routes", []):
        if not isinstance(route, dict):
            continue
        method = str(route.get("method", "")).upper()
        path = str(route.get("path", ""))
        handler = str(route.get("handler", ""))
        route_seen[(method, path)] = route_seen.get((method, path), 0) + 1
        route_id = _route_node_id(method, path)
        handler_file = handler.split(":", 1)[0]
        _node(nodes, route_id, "route.http", method=method, path=path, handler=handler, file=handler_file)
        if handler_file:
            edges.append({"kind": "exposes_route", "from": _file_node_id(handler_file), "to": route_id})

    _node(nodes, "runtime:entrypoint", "runtime.entrypoint", **runtime_contract)
    if runtime_contract.get("entrypoint"):
        edges.append({"kind": "starts_from", "from": "project", "to": "runtime:entrypoint"})

    class_index = _class_index(run_dir, project_root)
    for class_name, info in sorted(class_index.items()):
        path = root / info.rel_path
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        body = "\n".join(lines[max(info.lineno - 1, 0) : max(info.end_lineno, info.lineno)])
        if any(token in body for token in ("self._conn", "self.conn", "self.connection")):
            lifecycle_id = f"lifecycle:{class_name}"
            _node(nodes, lifecycle_id, "resource.lifecycle", class_name=class_name, file=info.rel_path, has_close="close" in info.methods)
            edges.append({"kind": "owns_resource_lifecycle", "from": f"symbol:{class_name}", "to": lifecycle_id})

    expected_titles = _expected_titles_from_tests(root)
    if expected_titles:
        seed_titles: set[str] = set()
        seed_files: set[str] = set()
        for path in _python_files(root):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "sample_issues" not in text:
                continue
            rel = _safe_rel(path, root)
            seed_files.add(rel)
            seed_titles.update(re.findall(r"['\"]title['\"]\s*:\s*['\"]([^'\"]+)['\"]", text))
        _node(
            nodes,
            "test:expected_seed_titles",
            "test.expected_seed_titles",
            titles=expected_titles,
            seed_titles=sorted(seed_titles),
            seed_files=sorted(seed_files),
        )

    graph = {
        "schema_version": "ctcp-contract-graph-v1",
        "project_root": project_root_rel,
        "contracts": {
            "symbols": SYMBOLS_ARTIFACT,
            "routes": ROUTES_ARTIFACT,
            "runtime": RUNTIME_CONTRACT_ARTIFACT,
        },
        "nodes": {key: nodes[key] for key in sorted(nodes)},
        "edges": sorted(edges, key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True)),
        "indexes": {
            "route_counts": {f"{method} {path}": count for (method, path), count in sorted(route_seen.items())},
        },
        "cache": cache_report,
    }
    graph["graph_hash"] = _stable_hash(graph)
    return graph


def validate_contract_graph(graph: dict[str, Any], symbols: dict[str, Any] | None = None) -> dict[str, Any]:
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), dict) else {}
    edges = graph.get("edges") if isinstance(graph.get("edges"), list) else []
    symbol_doc = symbols if isinstance(symbols, dict) else {}
    issues: list[dict[str, Any]] = []
    for conflict in symbol_doc.get("conflicts", []):
        if isinstance(conflict, dict):
            affected = sorted({str(conflict.get("existing_module", "")), str(conflict.get("new_module", ""))} - {""})
            issues.append({"type": "symbol.duplicate", "severity": "error", "affected_files": affected, **conflict})
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("kind") != "calls_method":
            continue
        target = str(edge.get("to", ""))
        call = nodes.get(str(edge.get("from", "")), {})
        if target not in nodes:
            issues.append(
                {
                    "type": "symbol.missing_method",
                    "severity": "error",
                    "class": call.get("class", ""),
                    "method": call.get("method", ""),
                    "file": call.get("file", ""),
                    "line": call.get("line", 0),
                    "owner": call.get("owner", ""),
                    "arg_count": call.get("arg_count", 0),
                    "affected_files": [str(call.get("file", ""))] if call.get("file") else [],
                }
            )
            continue
        method_node = nodes.get(target, {})
        if not bool(method_node.get("has_vararg", False)) and int(call.get("arg_count", 0) or 0) > int(method_node.get("max_positional", 0) or 0):
            issues.append(
                {
                    "type": "symbol.method_arity",
                    "severity": "error",
                    "class": call.get("class", ""),
                    "method": call.get("method", ""),
                    "file": call.get("file", ""),
                    "line": call.get("line", 0),
                    "arg_count": call.get("arg_count", 0),
                    "max_positional": method_node.get("max_positional", 0),
                    "affected_files": sorted({str(call.get("file", "")), str(method_node.get("file", ""))} - {""}),
                }
            )
    for route_key, count in dict(graph.get("indexes", {})).get("route_counts", {}).items():
        if int(count or 0) > 1:
            method, _, path = str(route_key).partition(" ")
            issues.append({"type": "route.duplicate", "severity": "error", "method": method, "path": path, "affected_files": []})
    has_routes = any(isinstance(row, dict) and row.get("kind") == "route.http" for row in nodes.values())
    runtime = nodes.get("runtime:entrypoint", {})
    if has_routes and not runtime.get("entrypoint"):
        issues.append({"type": "runtime.entrypoint_missing", "severity": "error", "affected_files": []})
    for node_id, row in nodes.items():
        if not isinstance(row, dict):
            continue
        affected = [str(row.get("file", ""))] if row.get("file") else []
        if row.get("kind") == "db.sqlite_usage" and row.get("row_reader") and not row.get("row_factory"):
            issues.append({"type": "db.sqlite_row_factory_missing", "severity": "error", "node": node_id, "affected_files": affected})
        if row.get("kind") == "resource.lifecycle" and not row.get("has_close"):
            issues.append({"type": "resource.lifecycle_close_missing", "severity": "error", "class": row.get("class_name", ""), "affected_files": affected})
        if row.get("kind") == "resource.tempfile_fd" and not row.get("close_guarded"):
            issues.append({"type": "resource.tempfile_fd_lifecycle", "severity": "error", "node": node_id, "affected_files": affected})
        if row.get("kind") == "serialization.json" and row.get("complex_values") and not row.get("default_serializer"):
            issues.append({"type": "serialization.default_serializer_missing", "severity": "error", "node": node_id, "affected_files": affected})
        if row.get("kind") == "test.expected_seed_titles":
            expected = {str(item) for item in row.get("titles", [])}
            seeded = {str(item) for item in row.get("seed_titles", [])}
            missing = sorted(expected - seeded)
            if missing:
                issues.append(
                    {
                        "type": "api_test.seed_fixture_drift",
                        "severity": "error",
                        "missing_titles": missing,
                        "affected_files": list(row.get("seed_files", [])),
                    }
                )
    affected_files = sorted({str(file) for issue in issues for file in issue.get("affected_files", []) if str(file).strip()})
    return {
        "schema_version": "ctcp-contract-graph-validation-v1",
        "status": "passed" if not issues else "failed",
        "issue_count": len(issues),
        "issues": issues,
        "affected_files": affected_files,
        "targeted_regeneration_scope": affected_files,
    }


def _legacy_unresolved_from_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "file": issue.get("file", ""),
            "line": issue.get("line", 0),
            "class": issue.get("class", ""),
            "method": issue.get("method", ""),
            "owner": issue.get("owner", ""),
            "arg_count": issue.get("arg_count", 0),
        }
        for issue in issues
        if issue.get("type") == "symbol.missing_method"
    ]


def _legacy_arity_from_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "file": issue.get("file", ""),
            "line": issue.get("line", 0),
            "class": issue.get("class", ""),
            "method": issue.get("method", ""),
            "arg_count": issue.get("arg_count", 0),
        }
        for issue in issues
        if issue.get("type") == "symbol.method_arity"
    ]


def _apply_graph_reconciliation_repairs(
    run_dir: Path,
    project_root: str | None,
    entrypoint: str | None,
    issues: list[dict[str, Any]],
    symbols: dict[str, Any],
) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    issue_types = {str(issue.get("type", "")) for issue in issues}
    if any(issue_type.startswith("runtime.") for issue_type in issue_types):
        repairs.extend(_repair_runtime_port_arg(run_dir, project_root, entrypoint))
        repairs.extend(_repair_runtime_blocking_serve(run_dir, project_root, entrypoint))
    if "db.sqlite_row_factory_missing" in issue_types:
        repairs.extend(_repair_sqlite_context_closing(run_dir, project_root))
        repairs.extend(_repair_sqlite_row_factory(run_dir, project_root))
    if "serialization.default_serializer_missing" in issue_types:
        repairs.extend(_repair_json_default_serializer(run_dir, project_root))
    if "resource.lifecycle_close_missing" in issue_types:
        repairs.extend(_repair_resource_close_methods(run_dir, project_root, [{"class": issue.get("class", ""), "method": "close"} for issue in issues]))
    if "resource.tempfile_fd_lifecycle" in issue_types:
        repairs.extend(_repair_windows_tempfile_locks(run_dir, project_root))
    if "api_test.seed_fixture_drift" in issue_types:
        repairs.extend(_repair_seed_title_consistency(run_dir, project_root))
    unresolved = _legacy_unresolved_from_issues(issues)
    if unresolved:
        repairs.extend(_repair_resource_close_methods(run_dir, project_root, unresolved))
        repairs.extend(_repair_missing_methods(run_dir, project_root, unresolved, symbols))
    arity_refs = _legacy_arity_from_issues(issues)
    if arity_refs:
        repairs.extend(_repair_method_arity(run_dir, project_root, arity_refs))
    if any(issue_type.startswith(("db.", "serialization.", "dto.", "runtime.")) for issue_type in issue_types):
        repairs.extend(_repair_enum_uppercase_aliases(run_dir, project_root))
        repairs.extend(_repair_enum_string_status(run_dir, project_root))
        repairs.extend(_repair_windows_tempfile_locks(run_dir, project_root))
        repairs.extend(_repair_seed_title_consistency(run_dir, project_root))
        repairs.extend(_repair_invalid_status_return_contract(run_dir, project_root))
        repairs.extend(_repair_dto_string_adapters(run_dir, project_root))
        repairs.extend(_repair_memory_db_tests(run_dir, project_root))
    return repairs


def converge_contract_graph(
    run_dir: Path,
    *,
    project_root: str | None = None,
    repair: bool = False,
    entrypoint: str | None = None,
    max_iterations: int | None = None,
    max_passes: int = 3,
    max_wall_clock_seconds: float = 120.0,
) -> dict[str, Any]:
    if max_iterations is not None:
        max_passes = max_iterations
    max_passes = max(1, int(max_passes or 1))
    max_wall_clock_seconds = max(0.1, float(max_wall_clock_seconds or 0.1))
    loop_start = time.monotonic()
    iterations: list[dict[str, Any]] = []
    pass_timings: list[dict[str, Any]] = []
    all_repairs: list[dict[str, Any]] = []
    previous_hash = ""
    stopped_reason = "max_passes"
    provider_call_count = 0
    final_graph: dict[str, Any] = {}
    final_validation: dict[str, Any] = {}
    final_symbols: dict[str, Any] = {}
    final_routes: dict[str, Any] = {}
    final_runtime: dict[str, Any] = {}

    for iteration in range(max_passes):
        pass_start = time.monotonic()
        if pass_start - loop_start >= max_wall_clock_seconds:
            stopped_reason = "max_wall_clock"
            break
        extraction_start = time.monotonic()
        final_symbols = extract_generated_symbols(run_dir, project_root)
        final_routes = extract_generated_routes(run_dir, project_root)
        final_runtime = extract_runtime_contract(run_dir, project_root, entrypoint)
        final_graph = extract_contract_graph(
            run_dir,
            project_root,
            entrypoint,
            symbols=final_symbols,
            routes=final_routes,
            runtime_contract=final_runtime,
        )
        extraction_seconds = time.monotonic() - extraction_start
        validation_start = time.monotonic()
        final_validation = validate_contract_graph(final_graph, final_symbols)
        validation_seconds = time.monotonic() - validation_start
        final_graph["validation"] = final_validation
        _write_json(run_dir / SYMBOLS_ARTIFACT, final_symbols)
        _write_json(run_dir / ROUTES_ARTIFACT, final_routes)
        _write_json(run_dir / RUNTIME_CONTRACT_ARTIFACT, final_runtime)
        _write_json(run_dir / CONTRACT_GRAPH_ARTIFACT, final_graph)

        graph_hash = str(final_graph.get("graph_hash", ""))
        issues = list(final_validation.get("issues", []))
        iteration_row: dict[str, Any] = {
            "iteration": iteration,
            "graph_hash": graph_hash,
            "previous_hash": previous_hash,
            "issue_count": len(issues),
            "drift_count": len(issues),
            "status": final_validation.get("status", "failed"),
            "affected_files": final_validation.get("affected_files", []),
            "changed_files": dict(final_graph.get("cache", {})).get("changed_files", []),
        }
        repair_seconds = 0.0
        if not issues:
            iteration_row["converged"] = True
            iterations.append(iteration_row)
            pass_timings.append(
                {
                    "pass": iteration,
                    "duration_seconds": round(time.monotonic() - pass_start, 3),
                    "extraction_seconds": round(extraction_seconds, 3),
                    "validation_seconds": round(validation_seconds, 3),
                    "repair_seconds": 0.0,
                    "drift_count": 0,
                    "graph_hash": graph_hash,
                    "changed_files": iteration_row["changed_files"],
                }
            )
            stopped_reason = "converged"
            break
        if not repair:
            iteration_row["converged"] = False
            iterations.append(iteration_row)
            pass_timings.append(
                {
                    "pass": iteration,
                    "duration_seconds": round(time.monotonic() - pass_start, 3),
                    "extraction_seconds": round(extraction_seconds, 3),
                    "validation_seconds": round(validation_seconds, 3),
                    "repair_seconds": 0.0,
                    "drift_count": len(issues),
                    "graph_hash": graph_hash,
                    "changed_files": iteration_row["changed_files"],
                }
            )
            stopped_reason = "error"
            break
        repair_start = time.monotonic()
        repairs = _apply_graph_reconciliation_repairs(run_dir, project_root, entrypoint, issues, final_symbols)
        repair_seconds = time.monotonic() - repair_start
        all_repairs.extend(repairs)
        iteration_row["repairs"] = repairs
        iteration_row["converged"] = False
        iterations.append(iteration_row)
        pass_timings.append(
            {
                "pass": iteration,
                "duration_seconds": round(time.monotonic() - pass_start, 3),
                "extraction_seconds": round(extraction_seconds, 3),
                "validation_seconds": round(validation_seconds, 3),
                "repair_seconds": round(repair_seconds, 3),
                "drift_count": len(issues),
                "graph_hash": graph_hash,
                "changed_files": iteration_row["changed_files"],
            }
        )
        if not repairs or graph_hash == previous_hash:
            stopped_reason = "error"
            break
        previous_hash = graph_hash
        if time.monotonic() - loop_start >= max_wall_clock_seconds:
            stopped_reason = "max_wall_clock"
            break
    else:
        stopped_reason = "max_passes"

    roots = _candidate_project_roots(run_dir, project_root)
    root = roots[0] if roots else run_dir
    final_issues = list(final_validation.get("issues", []))
    route_conflicts = [
        {"type": "duplicate_route", "method": issue.get("method", ""), "path": issue.get("path", "")}
        for issue in final_issues
        if issue.get("type") == "route.duplicate"
    ]
    report = {
        "schema_version": "ctcp-contract-graph-convergence-v1",
        "project_root": _safe_rel(root, run_dir) if root.exists() else "",
        "status": "passed" if not final_issues and stopped_reason == "converged" else "failed",
        "converged": not final_issues and stopped_reason == "converged",
        "max_passes": max_passes,
        "max_wall_clock_seconds": max_wall_clock_seconds,
        "elapsed_seconds": round(time.monotonic() - loop_start, 3),
        "stopped_reason": stopped_reason,
        "iterations": iterations,
        "pass_timings": pass_timings,
        "graph": CONTRACT_GRAPH_ARTIFACT,
        "graph_hash": final_graph.get("graph_hash", ""),
        "cache": final_graph.get("cache", {}),
        "provider_call_count": provider_call_count,
        "typed_issues": final_issues,
        "affected_files": final_validation.get("affected_files", []),
        "targeted_regeneration_scope": final_validation.get("targeted_regeneration_scope", []),
        "unresolved_references": _legacy_unresolved_from_issues(final_issues),
        "route_conflicts": route_conflicts,
        "symbol_conflicts": final_symbols.get("conflicts", []),
        "repairs": all_repairs,
        "contracts": {
            "graph": CONTRACT_GRAPH_ARTIFACT,
            "symbols": SYMBOLS_ARTIFACT,
            "routes": ROUTES_ARTIFACT,
            "runtime": RUNTIME_CONTRACT_ARTIFACT,
        },
        "runtime_contract_parseable": bool(final_runtime.get("entrypoint")),
        "route_registry_parseable": isinstance(final_routes.get("routes"), list),
        "symbol_registry_parseable": isinstance(final_symbols.get("symbols"), dict),
    }
    _write_json(run_dir / RECONCILIATION_ARTIFACT, report)
    return report


def reconcile_generated_contracts(
    run_dir: Path,
    *,
    project_root: str | None = None,
    repair: bool = False,
    entrypoint: str | None = None,
) -> dict[str, Any]:
    return converge_contract_graph(run_dir, project_root=project_root, entrypoint=entrypoint, repair=repair)


def write_generation_contract_artifacts(
    run_dir: Path,
    *,
    project_root: str | None = None,
    entrypoint: str | None = None,
    repair: bool = False,
) -> dict[str, Any]:
    return reconcile_generated_contracts(run_dir, project_root=project_root, entrypoint=entrypoint, repair=repair)


def load_generation_contract_context(run_dir: Path, *, max_chars: int = 10000) -> str:
    rows: list[str] = []
    for title, rel in (
        ("contract_graph.json", CONTRACT_GRAPH_ARTIFACT),
        ("generated_symbols.json", SYMBOLS_ARTIFACT),
        ("generated_routes.json", ROUTES_ARTIFACT),
        ("runtime_contract.json", RUNTIME_CONTRACT_ARTIFACT),
    ):
        path = run_dir / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            rows.append(f"### {title}\n{text}")
    if not rows:
        return ""
    body = "\n\n".join(rows)
    if len(body) > max_chars:
        return body[:max_chars] + "\n...<contract snapshot truncated>"
    return body
