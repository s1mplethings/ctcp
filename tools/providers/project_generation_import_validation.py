from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


def provider_interface_contract(src: dict[str, Any]) -> dict[str, Any]:
    sources = [src]
    if isinstance(src.get("manifest"), dict):
        sources.append(src["manifest"])
    for source in sources:
        for key in ("interfaces", "interface_contract"):
            value = source.get(key)
            if isinstance(value, dict):
                return value
    return {}


def _module_name_for_rel(rel: str) -> str:
    path = str(rel or "").strip().replace("\\", "/")
    if not path.endswith(".py"):
        return ""
    parts = path[:-3].split("/")
    if "src" in parts:
        parts = parts[parts.index("src") + 1 :]
    else:
        try:
            marker = next(i for i, part in enumerate(parts) if part == "project_output")
            parts = parts[marker + 2 :]
        except StopIteration:
            pass
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(part for part in parts if part and part != "scripts")


def _related_package_init_rels(rel: str) -> list[str]:
    path = str(rel or "").strip().replace("\\", "/")
    if not path.endswith(".py") or "/src/" not in path:
        return []
    prefix, tail = path.split("/src/", 1)
    parts = tail.split("/")
    if len(parts) < 2:
        return []
    out: list[str] = []
    for depth in range(1, len(parts)):
        init_rel = f"{prefix}/src/" + "/".join(parts[:depth] + ["__init__.py"])
        out.append(init_rel)
    return out


def _defined_python_symbols(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(str(node.name))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = list(getattr(node, "targets", [])) or [getattr(node, "target", None)]
            for target in targets:
                if isinstance(target, ast.Name):
                    out.add(str(target.id))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    out.add(str(alias.asname or alias.name))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                out.add(str(alias.asname or alias.name.split(".")[0]))
    return out


def _public_interface_symbols(tree: ast.AST, *, is_init: bool) -> set[str]:
    out: set[str] = set()
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(str(node.name))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = list(getattr(node, "targets", [])) or [getattr(node, "target", None)]
            for target in targets:
                if isinstance(target, ast.Name):
                    out.add(str(target.id))
        elif is_init and isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    out.add(str(alias.asname or alias.name))
    return {name for name in out if name and not name.startswith("_")}


def _contract_symbols(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    out: set[str] = set()
    for item in value:
        text = str(item or "").strip()
        if not text:
            continue
        if " import " in text:
            text = text.rsplit(" import ", 1)[-1]
        for part in text.replace("(", " ").replace(")", " ").split(","):
            symbol = part.strip().split(" as ", 1)[-1].strip()
            if symbol and symbol != "*":
                out.add(symbol)
    return out


def _interface_contract_mismatches(*, modules: dict[str, dict[str, Any]], interface_contract: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(interface_contract, dict) or not interface_contract:
        return []
    by_path = {str(meta.get("path", "")): meta for meta in modules.values()}
    mismatches: list[dict[str, Any]] = []
    for rel, row in interface_contract.items():
        path = str(rel or "").strip().replace("\\", "/")
        if "/src/" not in path:
            continue
        contract = row if isinstance(row, dict) else {}
        meta = by_path.get(path)
        if not meta:
            continue
        actual = _public_interface_symbols(meta["tree"], is_init=bool(meta.get("is_init", False)))
        declared = _contract_symbols(contract.get("defines")) | _contract_symbols(contract.get("exports"))
        if not declared:
            if actual:
                mismatches.append(
                    {
                        "path": path,
                        "reason": "actual public symbols were not declared in provider interface contract",
                        "actual_symbols": sorted(actual),
                        "declared_symbols": [],
                    }
                )
            continue
        missing_declared = sorted(declared - actual)
        undeclared_actual = sorted(actual - declared)
        if missing_declared or undeclared_actual:
            mismatches.append(
                {
                    "path": path,
                    "reason": "provider interface contract does not match generated Python file",
                    "missing_declared_symbols": missing_declared,
                    "undeclared_actual_symbols": undeclared_actual,
                    "actual_symbols": sorted(actual),
                    "declared_symbols": sorted(declared),
                }
            )
    return mismatches


def _import_graph_cycles(modules: dict[str, dict[str, Any]]) -> list[list[str]]:
    graph: dict[str, set[str]] = {name: set() for name in modules}
    for module_name, meta in modules.items():
        for node in ast.walk(meta["tree"]):
            if isinstance(node, ast.ImportFrom):
                target = _resolve_import_from_module(
                    current_module=module_name,
                    is_init=bool(meta.get("is_init", False)),
                    level=int(node.level or 0),
                    module=node.module,
                )
                if target in modules:
                    graph[module_name].add(target)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    target = str(alias.name)
                    if target in modules:
                        graph[module_name].add(target)
    cycles: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    def visit(node: str, stack: list[str]) -> None:
        if node in stack:
            cycle = stack[stack.index(node) :] + [node]
            key = tuple(sorted(cycle[:-1]))
            if key not in seen:
                seen.add(key)
                cycles.append(cycle)
            return
        for nxt in sorted(graph.get(node, set())):
            visit(nxt, stack + [node])

    for name in sorted(graph):
        visit(name, [])
    return cycles


def _resolve_import_from_module(*, current_module: str, is_init: bool, level: int, module: str | None) -> str:
    if level <= 0:
        return str(module or "").strip()
    parts = current_module.split(".") if is_init else current_module.split(".")[:-1]
    if level > 1:
        parts = parts[: max(0, len(parts) - (level - 1))]
    tail = str(module or "").strip()
    if tail:
        parts.extend(part for part in tail.split(".") if part)
    return ".".join(parts)


def python_import_consistency_validation(
    *,
    run_dir: Path,
    generated_business_files: list[str],
    startup_entrypoint: str,
    interface_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = []
    seen: set[str] = set()
    for raw in [startup_entrypoint] + list(generated_business_files):
        rel = str(raw or "").strip().replace("\\", "/")
        candidates = [rel]
        candidates.extend(_related_package_init_rels(rel))
        for candidate in candidates:
            if candidate and candidate.endswith(".py") and candidate not in seen:
                seen.add(candidate)
                rows.append(candidate)

    modules: dict[str, dict[str, Any]] = {}
    for rel in rows:
        module_name = _module_name_for_rel(rel)
        path = (run_dir / rel).resolve()
        if not module_name or not path.exists():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=rel)
        except SyntaxError:
            continue
        modules[module_name] = {
            "path": rel,
            "tree": tree,
            "symbols": _defined_python_symbols(tree),
            "is_init": Path(rel).name == "__init__.py",
        }

    missing: list[dict[str, str]] = []
    for module_name, meta in modules.items():
        for node in ast.walk(meta["tree"]):
            if not isinstance(node, ast.ImportFrom):
                continue
            target_module = _resolve_import_from_module(
                current_module=module_name,
                is_init=bool(meta.get("is_init", False)),
                level=int(node.level or 0),
                module=node.module,
            )
            target_meta = modules.get(target_module)
            if not target_meta:
                continue
            symbols = set(target_meta.get("symbols", set()))
            for alias in node.names:
                name = str(alias.name)
                if name == "*" or name in symbols:
                    continue
                missing.append(
                    {
                        "from_path": str(meta.get("path", "")),
                        "target_module": target_module,
                        "target_path": str(target_meta.get("path", "")),
                        "symbol": name,
                    }
                )
    interface_mismatches = _interface_contract_mismatches(modules=modules, interface_contract=interface_contract)
    import_cycles = _import_graph_cycles(modules)
    return {
        "checked_modules": sorted(modules),
        "missing_symbols": missing,
        "interface_contract_mismatches": interface_mismatches,
        "import_cycles": import_cycles,
        "passed": not missing and not interface_mismatches and not import_cycles,
    }
