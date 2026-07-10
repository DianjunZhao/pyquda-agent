# pyquda-agent

`pyquda-agent` is a helper repository for reading and analyzing `~/PyQUDA` without modifying it by default.

The repository is intended to support an AI-assisted workflow for:

- indexing the PyQUDA codebase
- generating reusable Python helper scripts
- writing architecture summaries and conventions notes
- answering code-reading questions with stable local artifacts

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

Current examples:

- [scripts/index_pyquda_repo.py](/Users/zhaodianjun/pyquda-agent/scripts/index_pyquda_repo.py)
- [scripts/render_pyquda_architecture.py](/Users/zhaodianjun/pyquda-agent/scripts/render_pyquda_architecture.py)
- [scripts/refresh_pyquda_analysis.py](/Users/zhaodianjun/pyquda-agent/scripts/refresh_pyquda_analysis.py)
- [docs/PYQUDA_ARCHITECTURE.md](/Users/zhaodianjun/pyquda-agent/docs/PYQUDA_ARCHITECTURE.md)
- [docs/CONVENTIONS.md](/Users/zhaodianjun/pyquda-agent/docs/CONVENTIONS.md)
- [data/pyquda_index.json](/Users/zhaodianjun/pyquda-agent/data/pyquda_index.json)

## First Milestone

The first useful version of this repository should be able to:

1. scan `~/PyQUDA` and build a machine-readable index
2. generate a human-readable architecture summary
3. document important PyQUDA conventions
4. provide a safe foundation for future query and assistant tooling

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

Quick syntax validation:

```bash
python3 -m py_compile scripts/*.py
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
