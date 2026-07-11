# First Workflow Audit

This document is generated from current workflow artifacts and records the audit state for:

- `pion_2pt_chroma_wall_local_zero_momentum_npy_v1`

## Requirements currently proved

- Retrieve implementation details from ~/pyquda-agent and ~/PyQUDA, especially runnable examples, tests, IO helpers, source helpers, inversion paths, contraction patterns, and output conventions.
- When local repository knowledge is insufficient for physics conventions, consult authoritative sources and record chosen conventions with citations.
- Parse the user request into a structured task specification instead of directly writing code.
- Detect underspecified fields and ask follow-up questions rather than inventing missing parameters.
- Distinguish physics choices, PyQUDA implementation choices, and cluster/runtime choices.
- Generate a complete Python script only after required fields are resolved.
- Refuse to label output as complete if placeholders, TODOs, fake helper calls, or guessed APIs remain.
- Validate generated scripts against real PyQUDA interfaces and example usage patterns.
- Generated script uses real PyQUDA imports, source/inversion/contraction APIs, and real gauge IO paths.
- Generated script is derived from and traceable to concrete upstream references in ~/PyQUDA.
- Generated complete script contains no TODO/pass/placeholder sections.
- The system explains which task fields were user-specified, clarified interactively, and which conventions were chosen from references.
- The system supports both --backend api and --backend codex.

## Requirements partially proved


## Requirements not yet fully proved

- Have local evidence that the current machine can numerically execute the generated script.

## Current evidence

- `data/pyquda_runtime_check.json`
- `data/run_pion_api_probe.json`
- `data/backend_parity.json`
- `data/runtime_candidates.json`
- `data/goal_audit.json`
- `outputs/run_pion_api.py`
- `outputs/run_pion_api.task.json`
- `outputs/run_pion_api.plan.json`

## Current blocker to full proof

- Runtime readiness status: `not_proved`.
- The active Python environment still lacks the runtime pieces needed for numerical execution: `cupy`, `pyquda`, and a working `pyquda_utils` import path tied to built PyQUDA core bindings.
- The direct script probe currently reaches runtime dependency preflight and stops there.

## Exit condition for this audit

1. `scripts/check_pyquda_runtime.py` reports `ready: true` for a real PyQUDA environment.
2. `scripts/probe_generated_workflow.py` reports `status: ok` for a generated complete pion 2pt script.
3. The resulting runtime evidence is captured in repository artifacts or documented command output.
