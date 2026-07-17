#!/usr/bin/env python3
"""Run a generated workflow script and record direct execution evidence."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pyquda_agent.python_version import ensure_supported_python

DEFAULT_SCRIPT = REPO_ROOT / "outputs" / "run_pion_api.py"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "run_pion_api_probe.json"

RUNTIME_GAP_MARKERS = (
    "Missing runtime dependency",
    "Unable to import 'pyquda_utils'",
    "Unable to import 'pyquda'",
)

INPUT_VISIBILITY_MARKERS = (
    "Gauge configuration not found:",
    "Propagator not found:",
)
OUTPUT_WRITABILITY_MARKERS = (
    "requires a writable parent directory on the submission filesystem",
    "Unable to locate an existing parent directory for",
)
ARTIFACT_CHAIN_MARKERS = (
    "Expected sibling review artifacts next to this script",
)
CLUSTER_ASSUMPTION_MARKERS = (
    "must be divisible by GRID_SIZE",
    "GRID_SIZE must",
    "LATTICE_SIZE must",
    "CLUSTER_LAUNCH must",
    "RESOURCE_PATH must",
)
HANDOFF_CONTRACT_MARKERS = (
    "Current pion",
    "Current proton",
    "Current rho/vector",
    "Current quark-propagator workflow requires",
    "Current Wilson-flow workflow requires",
    "Current APE-smear workflow requires",
    "Current HYP-smear workflow requires",
    "Current stout-smear workflow requires",
    "Expected a .npy",
    "Expected an .h5",
    "At least one source timeslice is required",
    "Duplicate propagator paths are not allowed",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute a generated workflow script and capture evidence.")
    parser.add_argument(
        "--script",
        type=Path,
        default=DEFAULT_SCRIPT,
        help="Path to the generated workflow script.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Where to write the JSON probe artifact.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Maximum execution time in seconds before terminating the script.",
    )
    parser.add_argument(
        "--pyquda-repo",
        type=Path,
        default=None,
        help="Optional PyQUDA checkout used for PYTHONPATH enrichment during probing.",
    )
    parser.add_argument(
        "--use-repo-pythonpath",
        action="store_true",
        help="Temporarily prepend --pyquda-repo to PYTHONPATH before executing the generated script.",
    )
    return parser.parse_args(argv)


def _blocked_probe_status(combined: str) -> tuple[str, str, str]:
    if any(marker in combined for marker in RUNTIME_GAP_MARKERS):
        return (
            "runtime_missing",
            "environment_missing",
            "Install or activate the missing runtime dependencies, then rerun the probe.",
        )
    if any(marker in combined for marker in INPUT_VISIBILITY_MARKERS):
        return (
            "input_visibility_blocked",
            "runtime_blocked",
            "Fix the input-path visibility on the target filesystem, then rerun the probe.",
        )
    if any(marker in combined for marker in OUTPUT_WRITABILITY_MARKERS):
        return (
            "output_writability_blocked",
            "runtime_blocked",
            "Choose or create a writable output directory on the target filesystem, then rerun the probe.",
        )
    if any(marker in combined for marker in ARTIFACT_CHAIN_MARKERS):
        return (
            "artifact_chain_missing",
            "runtime_blocked",
            "Restore the sibling .physics.json, .task.json, and .plan.json artifacts next to the generated script, then rerun the probe.",
        )
    if any(marker in combined for marker in CLUSTER_ASSUMPTION_MARKERS):
        return (
            "cluster_assumption_mismatch",
            "runtime_blocked",
            "Align lattice/grid/resource-path assumptions with the target cluster launch configuration, then rerun the probe.",
        )
    if any(marker in combined for marker in HANDOFF_CONTRACT_MARKERS):
        return (
            "handoff_contract_mismatch",
            "runtime_blocked",
            "Fix the generated-script handoff contract inputs or fixed workflow parameters, then rerun the probe.",
        )
    return (
        "probe_failed",
        "probe_failed",
        "Inspect stdout/stderr from the probe artifact, fix the remaining runtime-side failure, then rerun the probe.",
    )


def classify_probe(returncode: int, stdout: str, stderr: str) -> tuple[str, str, str]:
    if returncode == 0:
        return (
            "ok",
            "runtime_proved",
            "Runtime proof succeeded for this generated script.",
        )
    combined = "\n".join(part for part in (stdout, stderr) if part)
    return _blocked_probe_status(combined)


def build_probe(script_path: Path, timeout: float, *, pyquda_repo: Path | None = None, use_repo_pythonpath: bool = False) -> dict:
    resolved_script = script_path.expanduser().resolve()
    start = perf_counter()
    if not resolved_script.exists():
        return {
            "python": sys.executable,
            "script": str(resolved_script),
            "script_exists": False,
            "used_repo_pythonpath": use_repo_pythonpath,
            "pyquda_repo": str(pyquda_repo.expanduser().resolve()) if pyquda_repo is not None else None,
            "status": "missing_script",
            "runtime_level": "missing_script",
            "blocker_scope": "generation",
            "next_action": "Generate the script first, then rerun the probe.",
            "evidence_levels": {
                "syntax_valid": None,
                "structurally_grounded": None,
                "runtime_ready": False,
                "runtime_proved": False,
                "current_level": "missing_script",
                "blockers": ["generated script does not exist"],
            },
            "returncode": None,
            "duration_seconds": perf_counter() - start,
            "stdout": "",
            "stderr": "",
        }

    env = dict(os.environ)
    resolved_repo = pyquda_repo.expanduser().resolve() if pyquda_repo is not None else None
    if use_repo_pythonpath and resolved_repo is not None:
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(resolved_repo) if not existing_pythonpath else f"{resolved_repo}:{existing_pythonpath}"

    try:
        completed = subprocess.run(
            [sys.executable, str(resolved_script)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "python": sys.executable,
            "script": str(resolved_script),
            "script_exists": True,
            "used_repo_pythonpath": use_repo_pythonpath,
            "pyquda_repo": str(resolved_repo) if resolved_repo is not None else None,
            "status": "timeout",
            "runtime_level": "probe_timeout",
            "blocker_scope": "probe",
            "next_action": "Increase the probe timeout or reduce startup latency in the target runtime environment, then rerun the probe.",
            "evidence_levels": {
                "syntax_valid": None,
                "structurally_grounded": None,
                "runtime_ready": True,
                "runtime_proved": False,
                "current_level": "probe_timeout",
                "blockers": ["runtime probe timed out"],
            },
            "returncode": None,
            "duration_seconds": perf_counter() - start,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }
    except OSError as exc:
        return {
            "python": sys.executable,
            "script": str(resolved_script),
            "script_exists": True,
            "used_repo_pythonpath": use_repo_pythonpath,
            "pyquda_repo": str(resolved_repo) if resolved_repo is not None else None,
            "status": "probe_driver_failed",
            "runtime_level": "probe_driver_failed",
            "blocker_scope": "probe",
            "next_action": "Inspect the local probe harness error and repair the Python/subprocess environment before retrying the probe.",
            "evidence_levels": {
                "syntax_valid": None,
                "structurally_grounded": None,
                "runtime_ready": False,
                "runtime_proved": False,
                "current_level": "probe_driver_failed",
                "blockers": [f"Probe driver failed before script execution: {exc}"],
            },
            "returncode": None,
            "duration_seconds": perf_counter() - start,
            "stdout": "",
            "stderr": "",
        }

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    status, runtime_level, next_action = classify_probe(completed.returncode, stdout, stderr)
    blocker_scope = {
        "ok": None,
        "runtime_missing": "runtime",
        "input_visibility_blocked": "input",
        "output_writability_blocked": "output",
        "artifact_chain_missing": "artifact_chain",
        "cluster_assumption_mismatch": "cluster",
        "handoff_contract_mismatch": "implementation",
        "probe_failed": "runtime",
    }.get(status, "probe")
    blockers = [] if status == "ok" else ([stderr or stdout] if (stderr or stdout) else [status])
    return {
        "python": sys.executable,
        "script": str(resolved_script),
        "script_exists": True,
        "used_repo_pythonpath": use_repo_pythonpath,
        "pyquda_repo": str(resolved_repo) if resolved_repo is not None else None,
        "status": status,
        "runtime_level": runtime_level,
        "blocker_scope": blocker_scope,
        "next_action": next_action,
        "submission_checklist": [
            "Verify the generated script and sibling review artifacts are present on the submission filesystem.",
            "Verify runtime dependencies import in the target Python environment before heavy work starts.",
            "Verify input paths are visible to all ranks and output parents are writable on the target filesystem.",
            "Verify lattice/grid/resource-path assumptions still match the cluster launch layout.",
        ],
        "evidence_levels": {
            "syntax_valid": None,
            "structurally_grounded": None,
            "runtime_ready": status not in {"runtime_missing", "probe_driver_failed"},
            "runtime_proved": status == "ok",
            "current_level": runtime_level,
            "blockers": blockers,
        },
        "returncode": completed.returncode,
        "duration_seconds": perf_counter() - start,
        "stdout": stdout,
        "stderr": stderr,
    }


def main(argv: list[str] | None = None) -> int:
    ensure_supported_python(context="scripts/probe_generated_workflow.py")
    args = parse_args(argv)
    artifact = build_probe(
        args.script,
        args.timeout,
        pyquda_repo=args.pyquda_repo,
        use_repo_pythonpath=args.use_repo_pythonpath,
    )
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote workflow probe to {output}")
    return 0 if artifact["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
