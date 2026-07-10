#!/usr/bin/env python3
"""Build a reusable structural index for a local PyQUDA checkout."""

from __future__ import annotations

import argparse
import ast
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_REPO = Path.home() / "PyQUDA"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "pyquda_index.json"
DEFAULT_SCOPE = (
    "pyquda_core",
    "pyquda_utils",
    "pyquda_io",
    "pyquda_plugins",
    "tests",
    "examples",
)
EXCLUDED_PARTS = {"pycparser", "quda", ".git", ".github", "__pycache__"}
INTERNAL_IMPORT_PREFIXES = (
    "pyquda",
    "pyquda_comm",
    "pyquda_utils",
    "pyquda_io",
    "pyquda_plugins",
)
CYTHON_IMPORT_RE = re.compile(r"^\s*(?:from|cimport|from\s+\S+\s+cimport|import)\s+([A-Za-z0-9_\.]+)", re.MULTILINE)


@dataclass(frozen=True)
class ScopeSpec:
    name: str
    relative_path: str
    kind: str
    description: str


SCOPE_SPECS = (
    ScopeSpec("pyquda_core", "pyquda_core", "package-root", "Cython bindings, runtime package, and communication layer."),
    ScopeSpec("pyquda_utils", "pyquda_utils", "package-root", "High-level lattice utilities built on top of pyquda."),
    ScopeSpec("pyquda_io", "pyquda_io", "package-root", "Gauge and propagator file-format I/O helpers."),
    ScopeSpec("pyquda_plugins", "pyquda_plugins", "package-root", "Plugin scaffolding and optional compiled extensions."),
    ScopeSpec("tests", "tests", "validation", "Regression, smoke, and CLI coverage."),
    ScopeSpec("examples", "examples", "usage", "User-facing example workflows."),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index the local PyQUDA repository into JSON.")
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO, help="Path to the PyQUDA checkout. Defaults to ~/PyQUDA.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Where to write the generated JSON index.",
    )
    parser.add_argument(
        "--scope",
        nargs="+",
        choices=[spec.name for spec in SCOPE_SPECS],
        default=list(DEFAULT_SCOPE),
        help="Repository areas to index.",
    )
    return parser.parse_args()


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)


def normalize_python_module_basename(file_name: str) -> str | None:
    if file_name == "__init__.py":
        return "__init__"
    if not file_name.endswith(".py"):
        return None
    module_name = file_name[: -len(".py")]
    if module_name.endswith(".in"):
        module_name = module_name[: -len(".in")]
    return module_name


def guess_category(relative_path: Path) -> str:
    suffix = relative_path.suffix
    parts = set(relative_path.parts)
    name = relative_path.name
    if "tests" in parts or name.startswith("test_"):
        return "test"
    if "examples" in parts:
        return "example"
    if suffix in {".pyx", ".pxd", ".pxi"}:
        return "cython"
    if suffix == ".ipynb":
        return "notebook"
    if suffix in {".xml", ".ini"} or name.endswith(".ini.xml"):
        return "config"
    if name == "__init__.py":
        return "package-init"
    if suffix == ".py":
        return "python"
    return "other"


def iter_files(scope_root: Path) -> Iterable[Path]:
    for path in sorted(scope_root.rglob("*")):
        if path.is_file() and not should_skip(path.relative_to(scope_root.parent)):
            yield path


def module_name_from_path(repo_root: Path, file_path: Path) -> str | None:
    relative = file_path.relative_to(repo_root)
    basename = normalize_python_module_basename(file_path.name)
    if basename is None:
        return None
    normalized_parts = list(relative.parts[:-1]) + [basename]
    if relative.parts[0] == "tests":
        return basename if basename != "__init__" else ".".join(normalized_parts)
    if relative.parts[0] == "examples":
        return None
    module_parts = normalized_parts
    if relative.parts[0] == "pyquda_core":
        module_parts = module_parts[1:]
    if not module_parts:
        return None
    if module_parts[-1] == "__init__":
        module_parts = module_parts[:-1]
    return ".".join(module_parts) if module_parts else None


def parse_python_metadata(file_path: Path) -> dict:
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: list[str] = []
    classes: list[str] = []
    functions: list[str] = []
    all_exports: list[str] | None = None
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            base = "." * node.level + (node.module or "")
            imports.append(base)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    try:
                        value = ast.literal_eval(node.value)
                    except (ValueError, SyntaxError):
                        continue
                    if isinstance(value, list) and all(isinstance(item, str) for item in value):
                        all_exports = value
    return {
        "docstring": ast.get_docstring(tree),
        "imports": sorted(set(imports)),
        "classes": classes,
        "functions": functions,
        "exports": all_exports,
    }


def parse_cython_imports(file_path: Path) -> list[str]:
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    matches = CYTHON_IMPORT_RE.findall(text)
    return sorted(set(matches))


def classify_imports(imports: Iterable[str]) -> dict[str, list[str]]:
    internal: list[str] = []
    external: list[str] = []
    relative: list[str] = []
    for name in imports:
        if not name:
            continue
        if name.startswith("."):
            relative.append(name)
        elif name.startswith(INTERNAL_IMPORT_PREFIXES):
            internal.append(name)
        else:
            external.append(name)
    return {
        "internal": sorted(set(internal)),
        "external": sorted(set(external)),
        "relative": sorted(set(relative)),
    }


def infer_area(module_name: str) -> str | None:
    if module_name.startswith("pyquda_comm"):
        return "pyquda_core"
    if module_name.startswith("pyquda."):
        return "pyquda_core"
    if module_name == "pyquda":
        return "pyquda_core"
    if module_name.startswith("pyquda_utils"):
        return "pyquda_utils"
    if module_name.startswith("pyquda_io"):
        return "pyquda_io"
    if module_name.startswith("pyquda_plugins"):
        return "pyquda_plugins"
    if module_name.startswith("test_") or module_name.startswith("tests."):
        return "tests"
    return None


def validate_repo_root(repo_root: Path, scope_names: list[str]) -> list[ScopeSpec]:
    if not repo_root.exists():
        raise FileNotFoundError(f"PyQUDA repository not found: {repo_root}. Pass --repo to select the checkout.")
    if not repo_root.is_dir():
        raise NotADirectoryError(f"PyQUDA repository path is not a directory: {repo_root}")

    scope_specs = [spec for spec in SCOPE_SPECS if spec.name in scope_names]
    missing_scope_specs = [spec for spec in scope_specs if not (repo_root / spec.relative_path).exists()]
    if missing_scope_specs:
        requested = ", ".join(spec.relative_path for spec in scope_specs)
        missing = ", ".join(spec.relative_path for spec in missing_scope_specs)
        raise FileNotFoundError(
            f"Missing requested PyQUDA scopes under {repo_root}: {missing}. "
            f"Requested scopes: {requested}."
        )
    return scope_specs


def build_index(repo_root: Path, scope_names: list[str]) -> dict:
    scope_specs = validate_repo_root(repo_root, scope_names)
    files: list[dict] = []
    extension_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    area_file_counts: Counter[str] = Counter()
    dependency_edges: dict[str, Counter[str]] = defaultdict(Counter)
    python_modules: list[dict] = []

    for spec in scope_specs:
        scope_root = repo_root / spec.relative_path
        if not scope_root.exists():
            continue
        for file_path in iter_files(scope_root):
            relative = file_path.relative_to(repo_root)
            extension = file_path.suffix or "<none>"
            category = guess_category(relative)
            extension_counts[extension] += 1
            category_counts[category] += 1
            area_file_counts[spec.name] += 1
            module_name = module_name_from_path(repo_root, file_path)
            metadata = {
                "path": str(relative),
                "area": spec.name,
                "category": category,
                "extension": extension,
                "size_bytes": file_path.stat().st_size,
                "module_name": module_name,
            }
            if extension == ".py":
                py_meta = parse_python_metadata(file_path)
                metadata.update(py_meta)
                import_groups = classify_imports(py_meta["imports"])
                metadata["imports_grouped"] = import_groups
                python_modules.append(
                    {
                        "path": str(relative),
                        "module_name": module_name,
                        "area": spec.name,
                        "classes": py_meta["classes"],
                        "functions": py_meta["functions"],
                        "exports": py_meta["exports"],
                        "internal_imports": import_groups["internal"],
                        "external_imports": import_groups["external"],
                    }
                )
                for imported in import_groups["internal"]:
                    imported_area = infer_area(imported)
                    if imported_area and imported_area != spec.name:
                        dependency_edges[spec.name][imported_area] += 1
            elif extension in {".pyx", ".pxd", ".pxi"}:
                cython_imports = parse_cython_imports(file_path)
                metadata["imports"] = cython_imports
            files.append(metadata)

    top_level_packages = []
    for module in python_modules:
        name = module["module_name"]
        if not name:
            continue
        file_record = next(item for item in files if item["path"] == module["path"])
        if file_record["category"] == "package-init" and "." not in name:
            top_level_packages.append(
                {
                    "module_name": name,
                    "area": module["area"],
                    "path": module["path"],
                }
            )

    return {
        "repo_root": str(repo_root),
        "scopes": [
            {
                "name": spec.name,
                "relative_path": spec.relative_path,
                "kind": spec.kind,
                "description": spec.description,
                "exists": (repo_root / spec.relative_path).exists(),
            }
            for spec in scope_specs
        ],
        "excluded_parts": sorted(EXCLUDED_PARTS),
        "top_level_files": [p.name for p in sorted(repo_root.glob("*")) if p.is_file()],
        "summary": {
            "file_count": len(files),
            "python_module_count": sum(1 for item in files if item["extension"] == ".py"),
            "cython_file_count": sum(1 for item in files if item["extension"] in {".pyx", ".pxd", ".pxi"}),
            "extension_counts": dict(sorted(extension_counts.items())),
            "category_counts": dict(sorted(category_counts.items())),
            "area_file_counts": dict(sorted(area_file_counts.items())),
        },
        "dependency_edges": {
            area: dict(sorted(targets.items()))
            for area, targets in sorted(dependency_edges.items())
        },
        "top_level_packages": sorted(top_level_packages, key=lambda item: (item["area"], item["module_name"])),
        "python_modules": sorted(python_modules, key=lambda item: item["path"]),
        "files": sorted(files, key=lambda item: item["path"]),
    }


def main() -> int:
    args = parse_args()
    repo_root = args.repo.expanduser().resolve()
    output = args.output.expanduser().resolve()
    index = build_index(repo_root, args.scope)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote PyQUDA index to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
