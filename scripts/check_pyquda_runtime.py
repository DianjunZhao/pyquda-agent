#!/usr/bin/env python3
"""Check whether the current Python environment can import the runtime needed by generated PyQUDA scripts."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pyquda_agent.python_version import ensure_supported_python


DEFAULT_REPO = Path.home() / "PyQUDA"
MODULE_HINTS = {
    "numpy": "Install NumPy into the target Python environment used for PyQUDA handoff.",
    "cupy": "Use a GPU-enabled Python environment with CuPy installed and matching CUDA runtime support.",
    "pyquda": "Build or install the PyQUDA core bindings in this Python environment before runtime proof.",
    "pyquda_utils": "Expose the local PyQUDA checkout on PYTHONPATH or install pyquda_utils into the runtime environment.",
    "pyquda_utils.core": "Check that pyquda_utils is importable and that the built core helpers are present.",
}

SHORT_STEP_HINTS = {
    "cupy": "Install CuPy into the target Python environment.",
    "pyquda": "Build or install pyquda into the target Python environment.",
    "pyquda_utils": "Install the PyQUDA Python package or make the checkout importable in upstream-supported dev mode.",
    "pyquda_utils.core": "Ensure pyquda_utils.core is importable after installing/building PyQUDA.",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check whether the current Python can run generated PyQUDA scripts.")
    parser.add_argument(
        "--pyquda-repo",
        type=Path,
        default=DEFAULT_REPO,
        help="Path to the local PyQUDA checkout. Defaults to ~/PyQUDA.",
    )
    parser.add_argument(
        "--use-repo-pythonpath",
        action="store_true",
        help="Temporarily prepend the given PyQUDA checkout to sys.path before probing imports.",
    )
    return parser.parse_args(argv)


def _dedupe_preserve(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def probe_module(name: str) -> dict:
    try:
        module = importlib.import_module(name)
    except Exception as exc:
        return {
            "module": name,
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    return {
        "module": name,
        "ok": True,
        "path": getattr(module, "__file__", None),
    }


def _repo_pythonpath_diagnostic(*, use_repo_pythonpath: bool, blocker_details: list[dict]) -> dict:
    if not use_repo_pythonpath:
        return {
            "status": "not_attempted",
            "detail": "Re-run with --use-repo-pythonpath if you want to test whether the local checkout is discoverable without installation.",
        }
    pyquda_utils_blockers = [item for item in blocker_details if item["module"].startswith("pyquda_utils")]
    if not pyquda_utils_blockers:
        return {
            "status": "sufficient_for_discovery",
            "detail": "Adding the local checkout to PYTHONPATH was sufficient for pyquda_utils discovery in this probe.",
        }
    if any("pyquda_utils._version" in str(item.get("error") or "") for item in pyquda_utils_blockers):
        return {
            "status": "insufficient_checkout_layout",
            "detail": (
                "The checkout became partially visible on PYTHONPATH, but imports still failed because "
                "`pyquda_utils._version` is missing from the uninstalled layout. This indicates that plain "
                "repo-root PYTHONPATH is not enough; use the upstream install/dev-mode path."
            ),
        }
    return {
        "status": "still_missing",
        "detail": "Even with --use-repo-pythonpath, the checkout was not importable enough for runtime probing.",
    }


def _primary_blocker(blocker_details: list[dict]) -> dict | None:
    if not blocker_details:
        return None
    return {
        "category": blocker_details[0]["category"],
        "module": blocker_details[0]["module"],
        "error_type": blocker_details[0].get("error_type"),
        "error": blocker_details[0].get("error"),
    }


def _shortest_remaining_steps(blocker_details: list[dict], repo_pythonpath_diagnostic: dict) -> list[str]:
    steps = [SHORT_STEP_HINTS.get(item["module"], item["suggestion"]) for item in blocker_details]
    if repo_pythonpath_diagnostic.get("status") == "insufficient_checkout_layout":
        steps.append(
            "Follow the upstream install/dev-mode path instead of relying on repo-root PYTHONPATH alone."
        )
    return _dedupe_preserve([step for step in steps if step])


def build_report(pyquda_repo: Path, use_repo_pythonpath: bool) -> dict:
    repo = pyquda_repo.expanduser().resolve()
    if use_repo_pythonpath:
        sys.path.insert(0, str(repo))

    results = {
        "python": sys.executable,
        "pyquda_repo": str(repo),
        "used_repo_pythonpath": use_repo_pythonpath,
        "checks": [
            probe_module("numpy"),
            probe_module("cupy"),
            probe_module("pyquda"),
            probe_module("pyquda_utils"),
            probe_module("pyquda_utils.core"),
        ],
    }
    results["ready"] = all(item["ok"] for item in results["checks"])
    results["environment_ready"] = results["ready"]
    results["runtime_level"] = "runtime_ready" if results["ready"] else "environment_missing"
    blocker_details = [
        {
            "module": item["module"],
            "category": "module_missing",
            "error_type": item.get("error_type"),
            "error": item.get("error"),
            "suggestion": MODULE_HINTS.get(item["module"], "Inspect the failing import and align the Python environment with the target PyQUDA runtime."),
        }
        for item in results["checks"]
        if not item["ok"]
    ]
    next_actions = [item["suggestion"] for item in blocker_details]
    if blocker_details and not use_repo_pythonpath and any(item["module"].startswith("pyquda_utils") for item in blocker_details):
        next_actions.append("Re-run this check with --use-repo-pythonpath if you want to test whether the local ~/PyQUDA checkout is sufficient for import discovery.")
    repo_pythonpath_diagnostic = _repo_pythonpath_diagnostic(
        use_repo_pythonpath=use_repo_pythonpath,
        blocker_details=blocker_details,
    )
    results["evidence_levels"] = {
        "syntax_valid": None,
        "structurally_grounded": None,
        "runtime_ready": results["environment_ready"],
        "runtime_proved": False,
        "current_level": "runtime_ready" if results["environment_ready"] else "environment_missing",
        "blockers": blocker_details,
    }
    results["status"] = "ready" if results["ready"] else "environment_missing"
    results["blocker_categories"] = sorted({item["category"] for item in blocker_details})
    results["missing_modules"] = [item["module"] for item in blocker_details]
    results["next_actions"] = _dedupe_preserve(next_actions)
    results["primary_blocker"] = _primary_blocker(blocker_details)
    results["repo_pythonpath_diagnostic"] = repo_pythonpath_diagnostic
    results["shortest_remaining_steps"] = _shortest_remaining_steps(blocker_details, repo_pythonpath_diagnostic)
    results["submission_checklist"] = [
        {
            "kind": "python_interpreter",
            "status": "ok",
            "detail": f"Using interpreter {sys.executable}.",
        },
        {
            "kind": "module_imports",
            "status": "ok" if results["environment_ready"] else "blocked",
            "detail": (
                "All required runtime modules imported successfully."
                if results["environment_ready"]
                else "One or more required runtime modules are missing from the current Python environment."
            ),
        },
        {
            "kind": "repo_pythonpath",
            "status": "enabled" if use_repo_pythonpath else "disabled",
            "detail": (
                f"Temporarily prepended {repo} to PYTHONPATH for this probe."
                if use_repo_pythonpath
                else "Did not modify PYTHONPATH for this probe."
            ),
        },
    ]
    return results


def main(argv: list[str] | None = None) -> int:
    ensure_supported_python(context="scripts/check_pyquda_runtime.py")
    args = parse_args(argv)
    results = build_report(args.pyquda_repo, args.use_repo_pythonpath)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if results["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
