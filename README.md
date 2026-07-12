# pyquda-agent

`pyquda-agent` is a helper repository for reading and analyzing `~/PyQUDA` without modifying it by default.

The current primary workflow is not "natural language directly to code". It is:

`request -> structured task spec -> clarification -> reference-grounded plan -> complete script -> minimal validation`

The repository is intended to support an AI-assisted workflow for:

- indexing the PyQUDA codebase
- generating reusable Python helper scripts
- writing architecture summaries and conventions notes
- answering code-reading questions with stable local artifacts
- generating narrow, runnable PyQUDA scripts grounded in local references

## Scope

This repository is for analysis, not for upstream development inside `~/PyQUDA`.

Default boundary:

- read from `~/PyQUDA`
- write only inside this repository

If a task requires modifying `~/PyQUDA`, that should be an explicit user decision.

## Layout

- `scripts/`
  Python scripts for indexing, extracting, checking, and rendering repository information
- `docs/`
  Human-readable summaries, architecture notes, conventions, and process docs
- `data/`
  Generated indexes, caches, JSON outputs, and other derived artifacts
- `src/pyquda_agent/`
  Installable CLI package for task parsing, retrieval, clarification, session state, and script generation
- `tests/`
  Lightweight regression tests for indexers and the CLI MVP
- `pyproject.toml`
  Packaging metadata for the installable `pyquda-agent` command

Current examples:

- [scripts/index_pyquda_repo.py](/Users/zhaodianjun/pyquda-agent/scripts/index_pyquda_repo.py)
- [scripts/render_pyquda_architecture.py](/Users/zhaodianjun/pyquda-agent/scripts/render_pyquda_architecture.py)
- [scripts/refresh_pyquda_analysis.py](/Users/zhaodianjun/pyquda-agent/scripts/refresh_pyquda_analysis.py)
- [src/pyquda_agent/cli.py](/Users/zhaodianjun/pyquda-agent/src/pyquda_agent/cli.py)
- [src/pyquda_agent/app.py](/Users/zhaodianjun/pyquda-agent/src/pyquda_agent/app.py)
- [docs/PYQUDA_ARCHITECTURE.md](/Users/zhaodianjun/pyquda-agent/docs/PYQUDA_ARCHITECTURE.md)
- [docs/CONVENTIONS.md](/Users/zhaodianjun/pyquda-agent/docs/CONVENTIONS.md)
- [docs/RUN_WORKFLOW.md](/Users/zhaodianjun/pyquda-agent/docs/RUN_WORKFLOW.md)
- [docs/TASK_SCHEMAS.md](/Users/zhaodianjun/pyquda-agent/docs/TASK_SCHEMAS.md)
- [data/pyquda_index.json](/Users/zhaodianjun/pyquda-agent/data/pyquda_index.json)

## First Milestone

The first useful version of this repository should be able to:

1. scan `~/PyQUDA` and build a machine-readable index
2. generate a human-readable architecture summary
3. document important PyQUDA conventions
4. provide a safe foundation for future query and assistant tooling

## First Runnable Workflow

The first complete workflow is intentionally narrow:

- start from a gauge configuration
- `clover`
- `wall` source
- `local` sink
- zero momentum
- one pion 2pt correlator
- one `.npy` output path

This restriction is deliberate. The repository should not claim to support broad pion 2pt generation until one concrete path is traceable to real local PyQUDA examples and tests.

## Basic Workflow

Typical loop:

1. decide which `~/PyQUDA` subdirectories to inspect
2. run or update an indexing script in `scripts/`
3. write generated artifacts into `data/`
4. write findings and summaries into `docs/`
5. review outputs before committing

## Commands

Run a script:

```bash
python3 scripts/<name>.py
```

Run the installable CLI in-place:

```bash
PYTHONPATH=src python3 -m pyquda_agent.cli run "generate complete runnable pion 2pt from gauge ~/PyQUDA/tests/weak_field.lime with clover wall source local sink zero momentum timeslice 0 lattice size 4 4 4 8 grid 1 1 1 1 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed outputs/pion.npy outputs/run_pion.py resource_path=.cache/quda" --backend codex --no-interactive --output outputs/run_pion.py --pyquda-repo ~/PyQUDA
```

Or after installation:

```bash
pyquda-agent run "generate complete runnable pion 2pt from gauge ~/PyQUDA/tests/weak_field.lime with clover wall source local sink zero momentum timeslice 0 lattice size 4 4 4 8 grid 1 1 1 1 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed outputs/pion.npy outputs/run_pion.py resource_path=.cache/quda" --backend codex --no-interactive --output outputs/run_pion.py --pyquda-repo ~/PyQUDA
```

Quick syntax validation:

```bash
python3 -m py_compile scripts/*.py src/pyquda_agent/*.py
```

Check repository changes:

```bash
git status --short
```

Refresh the generated PyQUDA artifacts:

```bash
python3 scripts/refresh_pyquda_analysis.py
python3 scripts/refresh_pyquda_analysis.py --repo /path/to/PyQUDA
```

The scripts default to `~/PyQUDA` and fail fast if that checkout or the requested scopes are missing.

Optional local runtime check on this workstation:

```bash
python3 scripts/check_pyquda_runtime.py --pyquda-repo ~/PyQUDA
python3 scripts/check_pyquda_runtime.py --pyquda-repo ~/PyQUDA --use-repo-pythonpath
```

The run command also emits structured intermediates next to the script output:

- `*.task.json`
- `*.plan.json`

For the fixed pion-2pt workflow, `*.plan.json` may also include curated `external_citations` when physics-side conventions need support beyond local PyQUDA implementation references.

Current completion status for the first runnable workflow is tracked in [docs/FIRST_WORKFLOW_AUDIT.md](/Users/zhaodianjun/pyquda-agent/docs/FIRST_WORKFLOW_AUDIT.md).
The machine-readable audit summary lives in [data/goal_audit.json](/Users/zhaodianjun/pyquda-agent/data/goal_audit.json).

Refresh those audit artifacts from current evidence:

```bash
python3 scripts/refresh_goal_audit.py
```

Refresh the full first-workflow demo pipeline end to end:

```bash
python3 scripts/refresh_first_workflow_demo.py --pyquda-repo ~/PyQUDA --backend api
python3 scripts/refresh_first_workflow_demo.py --pyquda-repo ~/PyQUDA --backend codex
```

The default demo success criterion is now static HPC readiness, not local numerical execution. Add `--require-local-runtime-proof` only when you explicitly want the current workstation to prove it can run the generated script.

Check that `--backend api` and `--backend codex` produce identical fixed-workflow artifacts:

```bash
python3 scripts/check_backend_parity.py --pyquda-repo ~/PyQUDA
```

Scan local Python interpreters for an already-available PyQUDA runtime:

```bash
python3 scripts/scan_runtime_candidates.py --pyquda-repo ~/PyQUDA
```

If you also want local execution evidence and no candidate interpreter is ready, follow the local bootstrap notes in
[docs/PYQUDA_RUNTIME_BOOTSTRAP.md](/Users/zhaodianjun/pyquda-agent/docs/PYQUDA_RUNTIME_BOOTSTRAP.md).

Run the local tests:

```bash
python3 -B -m unittest tests.test_index_pyquda_repo tests.test_task_parser tests.test_clarifier tests.test_context_builder tests.test_generator tests.test_cli_run
```

## Design Rules

- Treat `~/PyQUDA` as read-only unless explicitly told otherwise.
- Prefer Python for new helper tooling.
- Make scripts repeatable and safe to rerun.
- Keep generated artifacts under `data/`.
- Keep explanatory material under `docs/`.
- Follow existing PyQUDA naming and physics conventions when they matter.

## Suggested Near-Term Tasks

- improve repository indexing coverage
- summarize important packages and entry points
- extract naming and data-layout conventions
- add small query utilities for locating relevant files or functions
- add lightweight tests once reusable logic grows

## Working Agreement

See [AGENTS.md](/Users/zhaodianjun/pyquda-agent/AGENTS.md) for the repository-specific instructions intended for Codex and similar agents.
