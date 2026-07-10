# Working Conventions

This repository is a local analysis workspace for `~/PyQUDA`.

## Scope

- Default behavior is read-only access to `~/PyQUDA`.
- Changes must stay inside this repository unless the user explicitly requests otherwise.

## Layout

- `scripts/`: repeatable helper and analysis scripts
- `docs/`: notes, findings, and process documentation
- `data/`: generated caches, indexes, and intermediate analysis artifacts

## Operating rules

- Prefer Python for new analysis tooling.
- Scripts should be rerunnable without manual cleanup.
- Before any task that reads `~/PyQUDA`, explicitly list the subdirectories to be inspected.
- If analysis depends on PyQUDA conventions, preserve the codebase's existing naming and physics conventions.

## Expected workflow

1. State which `~/PyQUDA` paths will be read.
2. Inspect the relevant source in read-only mode.
3. Place any new tooling in `scripts/`.
4. Place written findings in `docs/`.
5. Place generated indexes or caches in `data/`.
