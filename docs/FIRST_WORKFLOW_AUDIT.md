# Current Product Audit

This document is generated from current workflow artifacts and records the audit state for:

- support surface: `11` workflow families / `17` concrete grounded workflow targets
- family `pion_2pt`: `pion_2pt_chroma_wall_local_zero_momentum_npy_v1`, `pion_2pt_existing_propagator_local_zero_momentum_npy_v1`
- family `pion_pcac`: `pion_pcac_chroma_wall_local_zero_momentum_npy_v1`, `pion_pcac_existing_propagator_local_zero_momentum_npy_v1`
- family `pion_dispersion`: `pion_dispersion_chroma_point_momentum_npy_v1`
- family `meson_spec`: `meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1`, `meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1`
- family `proton_2pt`: `proton_2pt_chroma_wall_local_zero_momentum_npy_v1`, `proton_2pt_existing_propagator_local_zero_momentum_npy_v1`
- family `rho_vector`: `rho_vector_chroma_wall_local_zero_momentum_npy_v1`, `rho_vector_existing_propagator_local_zero_momentum_npy_v1`
- family `quark_propagator`: `quark_propagator_chroma_point_hdf5_v1`, `quark_propagator_gaussian_shell_chroma_hdf5_v1`
- family `ape_smear`: `ape_smear_chroma_qio_npy_v1`
- family `hyp_smear`: `hyp_smear_chroma_qio_npy_v1`
- family `stout_smear`: `stout_smear_chroma_qio_npy_v1`
- family `wilson_flow`: `wilson_flow_chroma_qio_energy_npy_v1`

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
- The system reliably selects among the currently supported workflow families from rough or direct runnable requests, with the pion_2pt family retaining both grounded gauge-entry and propagator-entry paths.
- Generated script is complete and HPC-ready: real APIs, explicit cluster/runtime assumptions, no placeholders, and suitable for handoff to a properly configured PyQUDA cluster environment.
- The main run path distinguishes generation success from execution/probe success and persists sibling probe artifacts for auditable runtime evidence.
- Validation artifacts preserve product-facing lifecycle evidence, including product_status plus generation/execution phases for both backend execution checks and supported-workflow integration checks.
- Product-behavior regression artifacts cover clarification routing, backend degradation, terminal execution awareness, terminal repair guidance, supported workflow generation, explicit unsupported refusal, and probe artifact consistency.
- Rough but reasonable supported requests enter clarification instead of collapsing into pseudocode or premature unsupported output.
- Explicit supported requests generate grounded scripts together with coherent generation/probe/runtime status reporting.
- Backend failures, network failures, runtime-environment blockers, and probe-harness failures expose clear next actions instead of silent degradation.
- Explicit unsupported requests expose the nearest grounded recovery path with either a copyable retry action or an explicit physics-choice gate, without letting backend-fix guidance override the main unsupported action.
- A realistic natural-language task suite covers ambiguous requests, explicit supported requests, and near-boundary unsupported variants with explicit nearest-grounded recovery expectations.
- Execution-readiness artifacts distinguish backend repairability, runtime dependency blockers, probe-harness failures, and runtime-side handoff blockers with explicit next actions.
- V13 validation artifacts distinguish codex usable vs fallback-only state and local runtime-proved vs exact remaining blockers without blurring those boundaries.

## Requirements partially proved


## Requirements not yet fully proved

- Optional: have local evidence that the current machine can numerically execute the generated script.

## Current evidence

- `data/pyquda_runtime_check.json`
- `data/run_pion_api_probe.json`
- `data/backend_parity.json`
- `data/backend_execution.json`
- `data/supported_workflows_validation.json`
- `data/v9_product_behavior.json`
- `data/v11_task_suite.json`
- `data/v12_execution_readiness.json`
- `data/v13_codex_runtime_readiness.json`
- `data/runtime_candidates.json`
- `data/goal_audit.json`
- `outputs/run_pion_api.py`
- `outputs/run_pion_api.physics.json`
- `outputs/run_pion_api.task.json`
- `outputs/run_pion_api.plan.json`
- `outputs/run_pion_api.probe.json`
- `outputs/run_pion_pcac.py`
- `outputs/validate_pion_dispersion.py`
- `outputs/run_meson_spec.py`
- `outputs/validate_proton_2pt.py`
- `outputs/validate_quark_propagator.py`
- `outputs/validate_ape_smear.py`
- `outputs/validate_hyp_smear.py`
- `outputs/run_stout_smear_api.py`

## Completion stance

- Grounded HPC handoff readiness status: `proved`.
- Backend execution usability summary: `api=usable, auto=usable, codex=usable`.
- Optional local runtime readiness status: `not_proved`.
- Supported workflow routing status: `proved`.
- Unified run/probe reporting status: `proved`.
- Product-facing validation-chain status: `proved`.
- V9 product-behavior regression status: `proved`.
- V9 rough-request clarification status: `proved`.
- V9 direct supported-generation status: `proved`.
- V9 actionable recovery-guidance status: `proved`.
- V9 unsupported actionability status: `proved`.
- V11 realistic task-suite regression status: `proved`.
- V12 execution-readiness status: `proved`.
- V13 codex/runtime-readiness status: `proved`.
- The repository default done condition is now: generate a complete, reference-grounded PyQUDA script with an auditable HPC handoff contract.
- Backend usability is audited separately through backend_execution artifacts; current usable backends do not imply local runtime proof, and local runtime blockers remain an independent evidence layer from grounded generation and HPC handoff readiness.
- Local runtime proof on this workstation remains a separate evidence layer; missing CuPy/PyQUDA runtime is treated as an environment limitation, not a blocker on grounded generation.

## Exit condition for this audit

1. `outputs/*.task.json` and `outputs/*.plan.json` fully resolve each supported workflow without unsupported fields.
2. Generated scripts remain traceable to concrete local PyQUDA references and pass placeholder-free static validation.
3. The scripts record explicit cluster/runtime assumptions for HPC handoff.
4. Optional: capture local runtime evidence when a usable PyQUDA environment happens to be available.
