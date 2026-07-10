# Repository Guidelines

## Purpose

`pyquda-agent` is a helper workspace for reading, indexing, and explaining `~/PyQUDA`.

This repository exists to:

- analyze the structure of `~/PyQUDA`
- generate reusable Python helper scripts
- write human-readable notes and summaries
- keep all generated artifacts out of the upstream `~/PyQUDA` tree

Default rule: treat `~/PyQUDA` as read-only unless the user explicitly asks to modify it.

## Project Structure

- `scripts/`: repeatable Python analysis and helper scripts
- `docs/`: architecture notes, conventions, findings, and workflow docs
- `data/`: generated indexes, caches, JSON summaries, and other derived artifacts
- `README.md`: project overview and quickstart
- `AGENTS.md`: repository operating rules for Codex and similar agents

Keep all new code, notes, and generated outputs inside this repository.

## Working Rules

Before reading `~/PyQUDA`, state which subdirectories will be inspected.

Good examples:

- `~/PyQUDA/pyquda_core`
- `~/PyQUDA/pyquda_utils`
- `~/PyQUDA/tests`
- `~/PyQUDA/examples`

Do not:

- edit files under `~/PyQUDA`
- write cache files into `~/PyQUDA`
- invent PyQUDA naming or physics conventions when the upstream repository already defines them

If a task depends on assumptions about lattice-QCD, field ordering, file formats, or phase conventions, prefer the conventions already used in `~/PyQUDA`.

## Script Design Expectations

Prefer Python for new tooling.

New scripts should be:

- idempotent
- safe to rerun
- explicit about input paths and output paths
- usable from the repository root

Preferred behavior:

- read from `~/PyQUDA`
- write derived results to `data/`
- write explanations or reports to `docs/`

Suggested naming patterns:

- `scripts/index_pyquda_*.py`
- `scripts/render_*.py`
- `scripts/check_*.py`
- `scripts/extract_*.py`

## Development Commands

There is no full build system yet. Use small local commands:

- `python3 scripts/<name>.py`
- `python3 -m py_compile scripts/*.py`
- `python3 -m unittest tests.test_index_pyquda_repo`
- `git status --short`

If a script grows beyond a single-file utility, factor reusable logic into a package later instead of embedding everything into one long script.

## Validation

For now, validate work by:

- checking Python syntax with `python3 -m py_compile scripts/*.py`
- running the target script against the intended read-only `~/PyQUDA` paths
- confirming that outputs land under `data/` or `docs/`
- documenting assumptions in `docs/` when behavior is non-obvious

If logic becomes nontrivial, start introducing small tests under a future `tests/` directory.

Do not commit local runtime caches such as `__pycache__/` or `*.pyc`.

## Commit and PR Guidance

Use short, imperative commit messages, for example:

- `Add PyQUDA repository indexer`
- `Render architecture summary from JSON index`
- `Document PyQUDA directory conventions`

PRs should say:

- what analysis goal the change supports
- which `~/PyQUDA` subdirectories were read
- which files were added or updated under `scripts/`, `docs/`, or `data/`
- how the change was verified

## First-Phase Priorities

When in doubt, prioritize work in this order:

1. repository indexing
2. architecture summaries
3. convention extraction
4. reusable helper scripts
5. lightweight query/report tooling

Concrete early deliverables:

- a script that indexes modules, classes, and functions from `~/PyQUDA`
- a generated JSON index under `data/`
- a human-readable architecture summary under `docs/`
- focused notes on important PyQUDA conventions
