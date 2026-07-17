# PyQUDA Runtime Bootstrap

This document records the local evidence-based bootstrap path needed to turn generated supported-workflow scripts from structurally validated artifacts into numerically runnable workflows.

All commands below require a Python interpreter that reports `>= 3.10`. If bare `python3` is older on your machine, export `PYTHON_BIN=/path/to/your/python` first and use that interpreter path consistently instead of copying `python3` literally.

## What the generated script needs

The current supported workflows currently require all of the following in one Python environment:

- `numpy`
- `cupy`
- `pyquda`
- `pyquda_utils`
- a valid `QUDA_PATH`
- working PyQUDA core bindings built against QUDA

The current machine audit shows that none of the scanned interpreters satisfy that full set.

## Upstream-supported install paths

The local `~/PyQUDA/README.md` and packaging files show two upstream-supported paths.

### Install from source

```bash
export QUDA_PATH=/path/to/quda/build/usqcd
cd ~/PyQUDA/pyquda_core
$PYTHON_BIN -m pip install .
cd ~/PyQUDA
$PYTHON_BIN -m pip install .
```

This matches:

- `~/PyQUDA/README.md`
- `~/PyQUDA/pyquda_core/pyproject.toml`
- `~/PyQUDA/pyproject.toml`

### Development / in-place mode

```bash
export QUDA_PATH=/path/to/quda/build/usqcd
cd ~/PyQUDA/pyquda_core
$PYTHON_BIN setup.py build_ext --inplace
cd ~/PyQUDA
$PYTHON_BIN setup.py egg_info
ln -s pyquda_core/pyquda_comm ./
ln -s pyquda_core/pyquda ./
```

This is the upstream-recommended development path when you want the repository root itself to behave like an importable checkout.

## Local install-script evidence

The local helper script `~/install_pyquda.sh` uses:

```bash
$PYTHON_BIN -m pip install --no-build-isolation -U .
cd ./pyquda_core/
$PYTHON_BIN -m pip install --no-build-isolation -U .
```

This suggests that in your existing local workflow, `--no-build-isolation` may be necessary or at least preferred.

## Current blockers observed on this machine

From `data/runtime_candidates.json` and `data/pyquda_runtime_check.json`:

- no scanned interpreter has `cupy`
- no scanned interpreter has `pyquda`
- `pyquda_utils` is not importable in the scanned environments
- adding `~/PyQUDA` to `PYTHONPATH` is not enough by itself

Additional local checkout evidence:

- `~/PyQUDA/tests/weak_field.lime` exists, so the current demo input gauge is already available locally
- `~/PyQUDA/pyquda_core/pyquda` and `~/PyQUDA/pyquda_core/pyquda_comm` source trees exist
- no compiled `*.so` or `*.dylib` artifacts were found under `~/PyQUDA/pyquda_core`
- no root-level development-mode symlinks such as `~/PyQUDA/pyquda` or `~/PyQUDA/pyquda_comm` are present

That means the remaining blocker is not missing workflow inputs; it is the absence of an importable built PyQUDA runtime in the currently scanned environments.

The newer execution-readiness surface in `data/v12_execution_readiness.json` now separates runtime blockers into:

- `module_missing`: the Python environment is missing `cupy`, `pyquda`, or `pyquda_utils`
- `probe_driver_failed`: the probe harness could not execute cleanly enough to assess the script
- `input_visibility_blocked`: gauge or propagator inputs are not visible on the target filesystem
- `output_writability_blocked`: the chosen output parent is not writable on the submission filesystem
- `cluster_assumption_mismatch`: lattice/grid/resource-path assumptions do not match the intended launch layout

Those categories are meant to drive pre-submit repair actions instead of collapsing every blocked run into a generic `runtime_missing`.

## Minimal completion path

To close the last unproved audit item on this machine:

1. activate or create one Python environment intended for PyQUDA
2. ensure `QUDA_PATH` points to the built QUDA tree
3. install or build `pyquda` and `pyquda_utils` in that environment
4. ensure `cupy` is installed in the same environment
5. rerun:

```bash
$PYTHON_BIN scripts/scan_runtime_candidates.py --pyquda-repo ~/PyQUDA
$PYTHON_BIN scripts/refresh_runtime_check.py --pyquda-repo ~/PyQUDA
$PYTHON_BIN scripts/probe_generated_workflow.py --script outputs/run_pion_api.py --output data/run_pion_api_probe.json
$PYTHON_BIN scripts/validate_v12_execution_readiness.py
$PYTHON_BIN scripts/refresh_goal_audit.py
```

The supported workflow suite can only be marked fully runtime-proved after one interpreter reports `ready: true` and generated script probes report `status: ok` for the scripts you care about.
