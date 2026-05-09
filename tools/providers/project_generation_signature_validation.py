from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class _Signature:
    name: str
    kind: str
    path: str
    line: int
    positional: tuple[str, ...]
    required_positional: tuple[str, ...]
    keyword_only: tuple[str, ...]
    required_keyword_only: tuple[str, ...]
    has_varargs: bool
    has_kwargs: bool

    def render(self) -> str:
        parts: list[str] = []
        for name in self.positional:
            parts.append(name if name in self.required_positional else f"{name}=...")
        if self.has_varargs:
            parts.append("*args")
        elif self.keyword_only:
            parts.append("*")
        for name in self.keyword_only:
            parts.append(name if name in self.required_keyword_only else f"{name}=...")
        if self.has_kwargs:
            parts.append("**kwargs")
        return f"{self.name}({', '.join(parts)})"


def python_signature_consistency_validation(
    *,
    run_dir: Path,
    startup_entrypoint: str,
    generated_business_files: list[str],
    interface_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidates = _candidate_python_files(
        run_dir=run_dir,
        startup_entrypoint=startup_entrypoint,
        generated_business_files=generated_business_files,
    )
    parsed: list[tuple[str, ast.Module]] = []
    parse_errors: list[dict[str, Any]] = []
    for rel, path in candidates:
        try:
            parsed.append((rel, ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=rel)))
        except SyntaxError as exc:
            parse_errors.append({"path": rel, "line": int(exc.lineno or 0), "message": str(exc.msg or "syntax error")})
    definitions, ambiguous = _collect_definitions(parsed)
    mismatches = _collect_mismatches(parsed, definitions)
    contract_mismatches = _contract_signature_mismatches(definitions, interface_contract)
    abstract_stubs = _abstract_stub_violations(parsed)
    return {
        "passed": not parse_errors and not mismatches and not contract_mismatches and not abstract_stubs,
        "checked_files": [rel for rel, _path in candidates],
        "definitions": len(definitions),
        "ambiguous_definitions": sorted(ambiguous),
        "parse_errors": parse_errors,
        "mismatches": mismatches,
        "interface_signature_mismatches": contract_mismatches,
        "abstract_stub_violations": abstract_stubs,
    }


def _candidate_python_files(
    *,
    run_dir: Path,
    startup_entrypoint: str,
    generated_business_files: list[str],
) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for raw in [startup_entrypoint, *generated_business_files]:
        rel = str(raw or "").strip().replace("\\", "/")
        if not rel or rel in seen or not rel.endswith(".py"):
            continue
        path = (run_dir / rel).resolve()
        if path.exists():
            seen.add(rel)
            out.append((rel, path))
    return out


def _collect_definitions(parsed: list[tuple[str, ast.Module]]) -> tuple[dict[str, _Signature], set[str]]:
    grouped: dict[str, list[_Signature]] = {}
    for rel, tree in parsed:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                sig = _class_signature(node, path=rel)
                grouped.setdefault(sig.name, []).append(sig)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if _is_nested_method(tree, node):
                    continue
                sig = _function_signature(node.name, node.args, path=rel, line=node.lineno, kind="function")
                grouped.setdefault(sig.name, []).append(sig)
    ambiguous = {name for name, rows in grouped.items() if len(rows) > 1}
    return {name: rows[0] for name, rows in grouped.items() if len(rows) == 1}, ambiguous


def _is_nested_method(tree: ast.Module, target: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and target in ast.walk(node):
            return True
    return False


def _class_signature(node: ast.ClassDef, *, path: str) -> _Signature:
    init = next(
        (
            child
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == "__init__"
        ),
        None,
    )
    if init is not None:
        return _function_signature(node.name, init.args, path=path, line=init.lineno, kind="class_constructor", drop_self=True)
    if _has_dataclass_decorator(node):
        return _dataclass_signature(node, path=path)
    return _Signature(node.name, "class_constructor", path, node.lineno, (), (), (), (), False, False)


def _function_signature(
    name: str,
    args: ast.arguments,
    *,
    path: str,
    line: int,
    kind: str,
    drop_self: bool = False,
) -> _Signature:
    positional_nodes = list(args.posonlyargs) + list(args.args)
    if drop_self and positional_nodes and positional_nodes[0].arg in {"self", "cls"}:
        positional_nodes = positional_nodes[1:]
    positional = tuple(arg.arg for arg in positional_nodes)
    required_count = max(0, len(positional_nodes) - len(args.defaults))
    required_positional = tuple(arg.arg for arg in positional_nodes[:required_count])
    keyword_only = tuple(arg.arg for arg in args.kwonlyargs)
    required_keyword_only = tuple(
        arg.arg for arg, default in zip(args.kwonlyargs, args.kw_defaults) if default is None
    )
    return _Signature(
        name,
        kind,
        path,
        line,
        positional,
        required_positional,
        keyword_only,
        required_keyword_only,
        bool(args.vararg),
        bool(args.kwarg),
    )


def _has_dataclass_decorator(node: ast.ClassDef) -> bool:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "dataclass":
            return True
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Name) and func.id == "dataclass":
                return True
            if isinstance(func, ast.Attribute) and func.attr == "dataclass":
                return True
    return False


def _dataclass_signature(node: ast.ClassDef, *, path: str) -> _Signature:
    positional: list[str] = []
    required: list[str] = []
    for child in node.body:
        field_name = ""
        has_default = False
        if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            field_name = child.target.id
            has_default = child.value is not None
        elif isinstance(child, ast.Assign) and len(child.targets) == 1 and isinstance(child.targets[0], ast.Name):
            field_name = child.targets[0].id
            has_default = True
        if not field_name or field_name.startswith("_"):
            continue
        positional.append(field_name)
        if not has_default:
            required.append(field_name)
    return _Signature(
        node.name,
        "dataclass_constructor",
        path,
        node.lineno,
        tuple(positional),
        tuple(required),
        (),
        (),
        False,
        False,
    )


def _collect_mismatches(parsed: list[tuple[str, ast.Module]], definitions: dict[str, _Signature]) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    for rel, tree in parsed:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node.func)
            if not name or name not in definitions:
                continue
            mismatch = _call_mismatch(node, definitions[name], caller_path=rel)
            if mismatch:
                mismatches.append(mismatch)
    return mismatches


def _contract_signature_mismatches(
    definitions: dict[str, _Signature],
    interface_contract: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(interface_contract, dict):
        return []
    by_path_name = {(sig.path, sig.name): sig for sig in definitions.values()}
    out: list[dict[str, Any]] = []
    for raw_path, row in interface_contract.items():
        path = str(raw_path or "").strip().replace("\\", "/")
        contract = row if isinstance(row, dict) else {}
        signatures = contract.get("signatures") or contract.get("signature_matrix")
        if not isinstance(signatures, dict):
            continue
        for raw_name, expected_raw in signatures.items():
            name = str(raw_name or "").strip()
            expected = str(expected_raw or "").strip()
            actual = by_path_name.get((path, name))
            if not name or not expected or not actual:
                continue
            actual_rendered = actual.render()
            if _normalized_signature(expected) != _normalized_signature(actual_rendered):
                out.append(
                    {
                        "path": path,
                        "symbol": name,
                        "declared_signature": expected,
                        "actual_signature": actual_rendered,
                        "line": actual.line,
                    }
                )
    return out


def _normalized_signature(value: str) -> str:
    return "".join(str(value or "").replace("=...", "").split())


def _abstract_stub_violations(parsed: list[tuple[str, ast.Module]]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for rel, tree in parsed:
        if "/tests/" in rel.replace("\\", "/"):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _raises_not_implemented(node):
                violations.append({"path": rel, "symbol": node.name, "line": int(node.lineno or 0)})
    return violations


def _raises_not_implemented(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Raise) or child.exc is None:
            continue
        exc = child.exc
        if isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
            return True
        if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name) and exc.func.id == "NotImplementedError":
            return True
    return False


def _call_name(func: ast.expr) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _call_mismatch(node: ast.Call, sig: _Signature, *, caller_path: str) -> dict[str, Any] | None:
    has_starargs = any(isinstance(arg, ast.Starred) for arg in node.args)
    positional_count = sum(1 for arg in node.args if not isinstance(arg, ast.Starred))
    keyword_names = [kw.arg for kw in node.keywords if kw.arg]
    keyword_set = set(keyword_names)
    missing = []
    if not has_starargs:
        for index, name in enumerate(sig.required_positional):
            if index >= positional_count and name not in keyword_set:
                missing.append(name)
    missing.extend(name for name in sig.required_keyword_only if name not in keyword_set)
    accepted_keywords = set(sig.positional) | set(sig.keyword_only)
    unexpected = [] if sig.has_kwargs else [name for name in keyword_names if name not in accepted_keywords]
    too_many_positionals = (
        not has_starargs
        and not sig.has_varargs
        and positional_count > len(sig.positional)
    )
    if not missing and not unexpected and not too_many_positionals:
        return None
    return {
        "caller_path": caller_path,
        "line": int(node.lineno or 0),
        "callee": sig.name,
        "callee_kind": sig.kind,
        "target_path": sig.path,
        "target_line": sig.line,
        "signature": sig.render(),
        "provided_positionals": positional_count,
        "provided_keywords": keyword_names,
        "missing_required": missing,
        "unexpected_keywords": unexpected,
        "too_many_positionals": too_many_positionals,
    }
