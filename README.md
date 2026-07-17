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

## Runtime Baseline

- Python `>= 3.10` is required for the CLI, validation scripts, and test suite.
- Local PyQUDA numerical execution is optional for repository completion. Generated scripts are considered complete when they are reference-grounded, placeholder-free, and come with auditable runtime/probe status.
- `~/PyQUDA` remains read-only by default.

## Python Command Convention

Before copying any command from this README or the workflow docs, make sure you are using a Python interpreter that reports `>= 3.10`.

```bash
python3 --version
export PYTHON_BIN=python3
```

If that version check prints `< 3.10`, do not keep using bare `python3`. Point `PYTHON_BIN` at an explicit supported interpreter instead, for example:

```bash
export PYTHON_BIN=/path/to/venv/bin/python
$PYTHON_BIN --version
```

All command examples below assume `PYTHON_BIN` already points to a Python `>= 3.10` interpreter. The installed `pyquda-agent` console command must come from that same environment.

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

## Supported Workflows

Current runnable support is intentionally narrow:
`11` workflow families / `17` concrete grounded workflow targets.

- workflow family `pion_2pt`
  grounded paths:
  `pion_2pt_chroma_wall_local_zero_momentum_npy_v1`
  `pion_2pt_existing_propagator_local_zero_momentum_npy_v1`
- workflow family `pion_pcac`
  grounded paths:
  `pion_pcac_chroma_wall_local_zero_momentum_npy_v1`
  `pion_pcac_existing_propagator_local_zero_momentum_npy_v1`
- workflow family `pion_dispersion`
  grounded path:
  `pion_dispersion_chroma_point_momentum_npy_v1`
- workflow family `meson_spec`
  grounded paths:
  `meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1`
  `meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1`
- workflow family `proton_2pt`
  grounded paths:
  `proton_2pt_chroma_wall_local_zero_momentum_npy_v1`
  `proton_2pt_existing_propagator_local_zero_momentum_npy_v1`
- workflow family `rho_vector`
  grounded paths:
  `rho_vector_chroma_wall_local_zero_momentum_npy_v1`
  `rho_vector_existing_propagator_local_zero_momentum_npy_v1`
- workflow family `quark_propagator`
  grounded paths:
  `quark_propagator_chroma_point_hdf5_v1`
  `quark_propagator_gaussian_shell_chroma_hdf5_v1`
- workflow family `ape_smear`
  grounded path:
  `ape_smear_chroma_qio_npy_v1`
- workflow family `hyp_smear`
  grounded path:
  `hyp_smear_chroma_qio_npy_v1`
- workflow family `stout_smear`
  grounded path:
  `stout_smear_chroma_qio_npy_v1`
- workflow family `wilson_flow`
  grounded path:
  `wilson_flow_chroma_qio_energy_npy_v1`

Each path stays pinned to concrete local PyQUDA references. Unsupported requests must remain explicit; the agent must not silently downgrade them into one of these paths.

## Current Product Boundary

What the current system does reliably:

- interpret rough pion / proton / meson-style requests and either enter clarification or map them to one supported grounded workflow
- keep rough `nucleon` / `baryon` requests in physics clarification until the baryon channel is explicit; the current grounded baryon path is proton 2pt only
- keep rough `propagator` requests on the grounded quark-propagator family, surfacing the point-source and gaussian-shell branches explicitly instead of collapsing back to meson clarification
- generate complete placeholder-free scripts only for the supported workflow catalog above
- emit auditable sibling artifacts such as `*.physics.json`, `*.task.json`, `*.plan.json`, and when requested `*.probe.json`
- distinguish product states such as `needs_input`, `generated_probe_available`, `generated_runtime_blocked`, `runtime_proved`, and `unsupported`
- keep backend degradation and runtime blockers explicit instead of pretending unsupported or unproven work is complete

What remains intentionally out of scope today:

- automatic support for new hadron channels beyond the grounded families above
- silent fallback from unsupported source/sink/momentum/operator combinations into "close enough" scripts
- claiming live online physics lookup is part of the default run path
- treating local runtime proof as required for repository-level completion

## Next Safe Expansions

The next safe expansion path is still depth-first, not breadth-first:

1. strengthen the existing supported families' execution-aware handoff and product validation
2. extend within an already grounded family only when the new branch is traceable to concrete local PyQUDA references
3. add a new workflow family only after it has the same artifact chain, refusal behavior, and runtime/probe reporting as the current families

Examples of acceptable next expansions:

- another narrowly grounded branch inside `pion_2pt`
- a new family backed by concrete `~/PyQUDA/examples` or `~/PyQUDA/tests` evidence

Examples of unacceptable expansion patterns:

- broad "all meson correlators" support with pseudocode fallbacks
- placeholder APIs or guessed helper names just to make a workflow look complete

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
$PYTHON_BIN scripts/<name>.py
```

Run the installable CLI in-place:

```bash
PYTHONPATH=src $PYTHON_BIN -m pyquda_agent.cli run "please compute the pion two-point correlator from gauge ~/PyQUDA/tests/weak_field.lime lattice size 4 4 4 8 grid 1 1 1 1 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed source timeslice 0 outputs/pion.npy outputs/run_pion.py resource_path=.cache/quda cluster_launch=local" --no-interactive --output outputs/run_pion.py --pyquda-repo ~/PyQUDA
```

Or after installation:

```bash
pyquda-agent run "please compute the pion two-point correlator from gauge ~/PyQUDA/tests/weak_field.lime lattice size 4 4 4 8 grid 1 1 1 1 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed source timeslice 0 outputs/pion.npy outputs/run_pion.py resource_path=.cache/quda cluster_launch=local" --no-interactive --output outputs/run_pion.py --pyquda-repo ~/PyQUDA
```

By default, `run` now uses `--backend auto`: it prefers local `codex`, may do a short local `codex` preflight, can switch to a configured API backend when that is the better fallback, and finally falls back to the rule-based path while recording the whole decision chain in artifacts.
If you want backend-assisted interpretation to fail fast instead of waiting for the default timeout, pass `--llm-timeout <seconds>`, for example `--backend codex --llm-timeout 5`.
For human-facing terminal use, add `--summary-only` to print the compact `result_summary` instead of the full artifact-rich JSON payload.
If you want an even more direct terminal-oriented readout, use `--result-format terminal` to print only the distilled terminal view instead of JSON.
That terminal mode renders a small card with `Outcome`, `Detail`, a concise `Reason` when the run is blocked or degraded, a compact `Status` block, key `Artifacts`, `Command`, and optional `Options`, where `Options` comes from `terminal_message.alternative_commands`.
It now also includes a short `Results` block so the normalized generation phase and execution/probe phase are visible without reading nested JSON.
It now also includes a `Checkpoint` line derived from `execution_checkpoint`, so a terminal user can tell immediately whether the run is still missing clarification, already generated but not probed, blocked by runtime environment, blocked by the probe harness, or fully runtime-proved.
For generated scripts, terminal mode now also includes a compact `Handoff` block that summarizes the current workflow's input/output directory boundaries and directory policies, so a user can review the cluster-facing storage assumptions without opening the full JSON or the emitted script.
It also surfaces `Continuation`, `Backend retry`, and `Runtime retry` lines when the current run is degraded or blocked, so a terminal user can see immediately whether to keep going with the current grounded path, reconfigure backend access, or rerun the probe.
When backend assistance degraded but the run can still continue on the grounded rule path, terminal mode now also surfaces `Backend fix`, `Backend fix detail`, and `Backend fix command`, so the “continue now” path and the “repair backend and retry later” path are visible together.
When execution evidence is blocked after script generation, terminal mode now also surfaces `Runtime fix`, `Runtime fix detail`, and `Runtime fix blocker`, so the user can distinguish “rerun the probe” from “what must be repaired first”.
Continuation hints generated during the same run still preserve `--result-format terminal`, so follow-up commands stay in the same human-facing mode.
That compact summary now also carries backend fallback diagnostics such as `llm_fallback_category` and `llm_fallback_reason`, plus a higher-level `backend_diagnostic` record that turns those categories into concrete next-step guidance such as configuring `--model`, adding credentials, running `codex login`, retrying with more timeout, or simply continuing with the current rule-based result.
It also surfaces `pending_question_prompts`, `pending_question_preview`, `pending_set_examples`, plus a more actionable `set_hint` with concrete example answers, so the next clarification step can usually be copied directly from the summary. Each preview item now also carries an `answer_kind`, and invalid `--reply` answers fail with the current question prompt plus an example reply instead of only showing an internal field name. The generated continuation commands also preserve the current run mode, such as backend choice, `--dry-run`, `--no-interactive`, and summary output mode.
For clients that want a small machine-readable batch summary instead of interpreting several hint fields separately, the summary now also exposes `clarification_status`, including whether clarification is active, the current batch fields, whether the preview is truncated, and whether `reply` or `set` is the recommended continuation mode.
For common parameter-heavy rounds, `clarification_status.field_groups` now also marks stable grouped subsets such as the current `clover_solver_parameters` batch.
When a stable grouped shorthand is relevant to the current round, `recommended_answer_mode` can now switch from `reply` to `set`, so the first suggested action is the shorter grouped `--set ...` continuation instead of a long ordered `--reply ...` chain.
The summary now also exposes `pending_group_set_examples` and `group_set_hint` whenever a stable grouped continuation is available, so the user can continue with a shorter grouped input like `--set clover_solver_parameters=0.09253,4.8965,...,1000` plus any remaining explicit fields instead of seven separate `--set` flags.
The same grouped path now also exists for geometry with `--set lattice_geometry=24,24,24,72;1,1,1,2`.
The preview lists stay intentionally short, but `set_hint` and `reply_hint` now try to cover the full current clarification batch rather than only the first three preview items, so one continuation command is more likely to clear the whole current round.
When clarification is blocked on physics-target confirmation, `missing_fields_*` now also surfaces `confirmed_target_id`, so summary consumers do not see a contradictory `needs_input` state with zero missing fields.
For task-level clarification, `missing_fields_preview` now follows the same priority as `pending_question_preview` and `next_action`, instead of exposing a raw schema-order slice that can disagree with the next suggested answer.
If `--llm-timeout` was set explicitly, the continuation commands preserve that timeout too.
`next_action` is also no longer a generic status string only; when clarification is active, it now stays short and product-facing by summarizing the current batch and candidate targets, while the full prompt and example answer remain in `pending_question_preview`, `questions`, and terminal `Next prompt` lines.
The compact summary now also carries a unified `workflow_outcome` object so you can see, in one place, whether the run is still blocked on clarification, only dry-run complete, script-generated, or script-generated-and-probed, together with the current runtime evidence level, blockers, and recommended next command.
For clients that want one stable top-level lifecycle label first, the same summary now also exposes `product_status`, for example `needs_input`, `ready_to_generate`, `generated_probe_available`, `generated_runtime_blocked`, `runtime_proved`, or `unsupported`.
It now also exposes `delivery_status`, a smaller product-facing split that answers three questions directly: did generation complete, what happened with runtime proof, and what is the current primary next step.
For thinner callers that only need those two lifecycle answers, the same summary now also exposes `generation_result` and `execution_result` as smaller mirrored cards.
For callers that want the whole `rough request -> clarification -> generation -> probe/runtime` chain in one stable place, the same summary now also exposes `workflow_lifecycle`, which folds the current stage, blocking gate, generation substate, runtime substate, next action, and emitted artifact paths into one compact object.
The same summary now also exposes `runtime_diagnostic`, which separates at least `probe_available`, `runtime_missing`, `probe_driver_failed`, and `runtime_proved`, so “missing runtime environment” stays distinct from “the probe harness itself failed”.
For callers that want one shorter execution-aware product card than `workflow_lifecycle`, the same summary now also exposes `execution_checkpoint`, which records the current checkpoint state, runtime level, probe status, handoff readiness, and the next artifact/action without forcing the client to merge several nested fields.
The same summary now also exposes `backend_path`, a thinner backend-degradation record that says which backend was requested, which backend actually ran, whether the current grounded result is still usable, and what repair action is available if the user wants LLM assistance restored.
For HPC handoff, the same summary now also exposes `hpc_handoff`, which mirrors the generated script's submission contract: input paths, output paths, rank-0 write policy, required runtime modules, probe artifact path, and the preflight checks that should be reviewed before cluster submission.
For local `codex` usage, a short preflight timeout no longer always forces an immediate build-time fallback to rules. In the current path, `auto` mode without a configured API backup, and explicit `--backend codex`, keep the codex backend alive after a short timeout preflight and let the real LLM call decide whether fallback is actually necessary. For the smallest rough normalization-only requests, `auto` mode without a configured API backup can now skip codex preflight entirely and record `llm_codex_preflight_skipped` / `llm_codex_preflight_skip_reason` instead of paying fixed preflight latency before the real backend call. The artifact chain records both behaviors explicitly under the `llm_codex_preflight_*` fields and the mirrored backend-diagnostic fields.
When a run resumes from a saved session, `auto` mode may also reuse the last backend outcome to avoid re-trying a recently degraded codex path before attempting an available API route. The summary distinguishes `llm_session_backend_memory_considered` from `llm_session_backend_memory_used`, so callers can tell the difference between “this memory influenced backend choice” and “this memory led to a successful alternative backend path.”
The intent-interpretation prompt is now deliberately compact too: it sends a reduced physics snapshot with counts for curated citations and local references instead of inlining the full citation JSON and reference lists, so backend-assisted rough-request interpretation does not pay unnecessary prompt-size overhead.
For clearly identified rough requests such as simple pion/proton two-point asks, that first prompt now also omits detailed formula/operator proposal payloads and reserves them for genuinely ambiguous interpretation cases.
When a request is genuinely ambiguous, the emitted summary and terminal view now also surface a short `physics_formula_preview`, so the user can see candidate operators/conventions before answering the clarification question.
The same summary now also exposes `physics_workflow_preview`, which maps each candidate physics target onto the currently grounded workflow targets, so the user can see which interpretations are already runnable and which ones would still stay unsupported.
For local `codex`, the rough single-target path is now even narrower: when the rule-based layer already has one plausible unconfirmed target, the first backend-assisted stage becomes normalization-only instead of a full interpretation rewrite. The artifact chain records this through `llm_intent_strategy` and `llm_intent_prompt_profile`.
For explicit `--backend codex` on that same rough normalization-only path, the run now also skips codex preflight entirely and records `llm_codex_preflight_skipped` / `llm_codex_preflight_skip_reason`, because the real codex call is the first meaningful backend signal for that tiny request shape.
If that normalization-only codex call still times out, the agent now skips a second low-value retry and records `llm_timeout_recovery_skipped` / `llm_timeout_recovery_skip_reason` instead of spending another bounded timeout on the same tiny request shape.
If a backend-assisted intent call still times out, the resolver now does at most one explicit timeout-recovery retry with an even smaller prompt and a shorter bounded backend timeout before declaring final fallback. The artifact chain records whether that recovery attempt was attempted, used, or failed.
For local `codex`, the first intent-interpretation call is now also capped separately from the backend's general timeout budget, so rough-request clarification does not have to spend the full backend timeout before recovery/fallback starts. That primary cap is recorded under `llm_intent_primary_timeout_seconds`.
That cap is now strategy-aware too: the rough `normalization_only` codex path uses a shorter first-attempt cap than the heavier full-interpretation path.
For clients that want one even smaller status card, the same summary now also exposes `capability_summary`, which compresses the current backend capability, generation capability, runtime-evidence capability, and primary next action into one compact object while still preserving the more detailed `workflow_outcome`, `delivery_status`, and `backend_diagnostic` records.
For even faster terminal use, the summary now also exposes `action_queue`, a small ordered list of next actions such as `continue_by_reply`, `continue_by_set`, `generate_script`, `run_probe`, `retry_probe`, `runtime_fix`, or `backend_fix`.
The clarification-related actions now also include the current batch fields directly in their titles/guidance, so a UI can surface a usable next-step label without recomputing batch context from other fields.
When the run stops at `dry_run`, `resume_hint` intentionally preserves the original mode, while the `generate_script` action in `action_queue` and `primary_action` removes `--dry-run` so the first suggested command actually emits the script.
The first item is also mirrored as `primary_action`, and each action now carries an `action_state`: `ready`, `conditional`, or `blocked`. `actionable` stays `true` only for `ready` actions. When an action still depends on missing credentials, connectivity, or service recovery, `actionability_reason` explains the prerequisite.
For UI clients that want one compact status card, the summary now also exposes `run_overview`, which condenses the current phase, headline, blocking kind, backend state, runtime level, and the primary action identity into a single object.
For explicit unsupported requests, the same summary now also makes the nearest grounded recovery path more reviewable by exposing scope-separated `physics` / `implementation` / `runtime` deltas for each nearby workflow, instead of only returning a flat unsupported reason string.
The product-facing summary vocabulary and examples now live in:

- [docs/RESULT_SUMMARY_TAXONOMY.md](/Users/zhaodianjun/pyquda-agent/docs/RESULT_SUMMARY_TAXONOMY.md)
- [docs/RESULT_SUMMARY_STATUS_MAPPING.md](/Users/zhaodianjun/pyquda-agent/docs/RESULT_SUMMARY_STATUS_MAPPING.md)
- [docs/RESULT_SUMMARY_EXAMPLES.md](/Users/zhaodianjun/pyquda-agent/docs/RESULT_SUMMARY_EXAMPLES.md)

If you do not want to use internal field names at all, you can continue with repeated `--reply` answers in pending-question order, for example `--reply pion --reply gauge --reply 0`.
When continuing a partially specified request, you can also apply clarification answers directly with repeated `--set field=value`, for example:
`--resume-session outputs/run_pion.session.json --set mass=0.09253 --set source_timeslices=0`.
When the current clarification round exposes a complete `clover_solver_parameters` group, you can also use the grouped shorthand:
`--resume-session outputs/run_pion.session.json --set clover_solver_parameters=0.09253,4.8965,0.86679,0.8549165664,2.32582045,1e-12,1000`.
For geometry rounds, you can similarly use:
`--resume-session outputs/run_pion.session.json --set lattice_geometry=24,24,24,72;1,1,1,2`.
After a script is generated, the result also exposes `probe_hint`, a copyable command for the next runtime-proof step.
When `--runtime-probe` is used, the same run now records whether probe execution was requested or actually attempted under `runtime_evidence.probe_policy`, so the artifact chain distinguishes default opt-in probe policy from this run's concrete execution path.
If the probe harness itself fails before the generated script can be assessed, the main `run` result still keeps the emitted script and records `execution_status=probe_driver_failed` plus a structured `probe_driver_error` in the probe artifact instead of aborting the whole generation path.
If the natural-language request mentions relative paths like `outputs/run_pion.py` or `outputs/pion.npy`, the run path now resolves them under the current runtime output root instead of accidentally escaping to a parent directory.
The full `context` payload now also exposes `index_provenance`. If the loaded local index was built for a different PyQUDA checkout than the current `--pyquda-repo`, the run marks `status=repo_mismatch` so callers do not silently treat the stored `index_summary` as counts for the current repo.
The compact summary now mirrors the same `index_provenance` record, so `--summary-only` users do not need the full payload just to detect an index/repo mismatch.

Quick syntax validation:

```bash
$PYTHON_BIN -m py_compile scripts/*.py src/pyquda_agent/*.py
```

Check repository changes:

```bash
git status --short
```

Refresh the generated PyQUDA artifacts:

```bash
$PYTHON_BIN scripts/refresh_pyquda_analysis.py
$PYTHON_BIN scripts/refresh_pyquda_analysis.py --repo /path/to/PyQUDA
```

The scripts default to `~/PyQUDA` and fail fast if that checkout or the requested scopes are missing.

Optional local runtime check on this workstation:

```bash
$PYTHON_BIN scripts/check_pyquda_runtime.py --pyquda-repo ~/PyQUDA
$PYTHON_BIN scripts/check_pyquda_runtime.py --pyquda-repo ~/PyQUDA --use-repo-pythonpath
```

The run command also emits structured intermediates next to the script output:

- `*.physics.json`
- `*.task.json`
- `*.plan.json`
- `*.probe.json` when `--runtime-probe` is enabled

These artifacts also record the current knowledge boundary:

- local curated citation JSON is implemented
- model inference may be used when a backend is available
- live online lookup is opt-in, provenance-tagged, and only used to enrich physics-side clarification when local PyQUDA evidence and curated local citations are insufficient
- live online lookup does not count as local PyQUDA implementation grounding and does not auto-confirm a runnable workflow

## Completion Semantics

Repository-level `complete` means:

- the task resolved to one grounded supported path
- the emitted Python script uses real PyQUDA imports and local-reference-grounded APIs
- sibling `*.physics.json`, `*.task.json`, and `*.plan.json` artifacts exist
- runtime/probe state is reported explicitly as `structurally_grounded`, `runtime_ready`, or `runtime_proved`

It does not mean this workstation already has a runnable PyQUDA environment. That boundary is tracked separately in runtime artifacts and in [docs/PYQUDA_RUNTIME_BOOTSTRAP.md](/Users/zhaodianjun/pyquda-agent/docs/PYQUDA_RUNTIME_BOOTSTRAP.md).

Current completion status for the supported workflow suite is tracked in [docs/FIRST_WORKFLOW_AUDIT.md](/Users/zhaodianjun/pyquda-agent/docs/FIRST_WORKFLOW_AUDIT.md).
The machine-readable audit summary lives in [data/goal_audit.json](/Users/zhaodianjun/pyquda-agent/data/goal_audit.json).

Refresh those audit artifacts from current evidence:

```bash
$PYTHON_BIN scripts/refresh_goal_audit.py
```

Refresh the real backend execution report:

```bash
$PYTHON_BIN scripts/validate_backend_execution.py --pyquda-repo ~/PyQUDA
```

That report now summarizes each backend as `usable`, `mixed`, `fallback_only`, or `incoherent`, instead of only dumping raw case payloads.
It also checks that rough-request runs keep the expected product-facing clarification shape, including `product_status=needs_input` together with coherent `generation_result` / `execution_result` phases.

Refresh the v11 natural-language task-suite regression report:

```bash
$PYTHON_BIN scripts/validate_v11_task_suite.py
```

That report writes [data/v11_task_suite.json](/Users/zhaodianjun/pyquda-agent/data/v11_task_suite.json) and checks current summary-contract behavior for ambiguous meson asks, explicit supported requests, propagator/smear/flow requests, and explicit unsupported edge cases.
It now also covers unsupported propagator / smear / flow boundary variants, so nearest-grounded repair scope stays visible across those families instead of only in isolated CLI tests.

Refresh the v12 execution-readiness report:

```bash
$PYTHON_BIN scripts/validate_v12_execution_readiness.py
```

That report writes [data/v12_execution_readiness.json](/Users/zhaodianjun/pyquda-agent/data/v12_execution_readiness.json) and checks whether backend fallback paths remain repairable and whether runtime blockers are classified as dependency, probe-harness, input-visibility, output-writability, or cluster-assumption issues.

Refresh the demo pipeline end to end for the reference supported workflow:

```bash
$PYTHON_BIN scripts/refresh_first_workflow_demo.py --pyquda-repo ~/PyQUDA --backend api
$PYTHON_BIN scripts/refresh_first_workflow_demo.py --pyquda-repo ~/PyQUDA --backend codex
```

These demo refreshes now use the main `run` path as the default generation-and-probe workflow. The default demo success criterion is static HPC readiness, not local numerical execution. Add `--require-local-runtime-proof` only when you explicitly want the current workstation to prove it can run the generated script.

Check that `--backend api` and `--backend codex` produce identical artifacts for one supported workflow:

```bash
$PYTHON_BIN scripts/check_backend_parity.py --pyquda-repo ~/PyQUDA
```

Scan local Python interpreters for an already-available PyQUDA runtime:

```bash
$PYTHON_BIN scripts/scan_runtime_candidates.py --pyquda-repo ~/PyQUDA
```

If you also want local execution evidence and no candidate interpreter is ready, follow the local bootstrap notes in
[docs/PYQUDA_RUNTIME_BOOTSTRAP.md](/Users/zhaodianjun/pyquda-agent/docs/PYQUDA_RUNTIME_BOOTSTRAP.md).

Run the local tests:

```bash
$PYTHON_BIN -B -m unittest tests.test_index_pyquda_repo tests.test_task_parser tests.test_clarifier tests.test_context_builder tests.test_generator tests.test_cli_run tests.test_validate_supported_workflows tests.test_validate_backend_execution
```

## Current Validation Gate

Use these commands as the current closeout gate. All of them require `PYTHON_BIN` to be Python `>= 3.10`.

```bash
$PYTHON_BIN -B -m unittest
$PYTHON_BIN scripts/validate_backend_execution.py --pyquda-repo ~/PyQUDA
$PYTHON_BIN scripts/validate_supported_workflows.py --pyquda-repo ~/PyQUDA --backend api
$PYTHON_BIN scripts/validate_v9_product_behavior.py
$PYTHON_BIN scripts/validate_v11_task_suite.py
$PYTHON_BIN scripts/validate_v12_execution_readiness.py
$PYTHON_BIN scripts/refresh_goal_audit.py
```

Interpret these gates narrowly:

- Grounded generation / handoff proved:
  `scripts/validate_supported_workflows.py`, `scripts/validate_v9_product_behavior.py`, `scripts/validate_v11_task_suite.py`, and `scripts/refresh_goal_audit.py` prove the current `11` families / `17` grounded targets remain coherent, auditable, and suitable for HPC handoff in principle.
- Backend usable:
  `scripts/validate_backend_execution.py` proves whether `auto` / `api` / `codex` are currently usable in the real CLI path, or whether they remain explicit fallback-only backend routes.
  As of July 17, 2026, the latest real report shows `api=usable`, `auto=usable`, and `codex=usable`.
- Local runtime proved:
  none of the default closeout gates prove that this workstation can numerically execute PyQUDA end to end unless a probe actually reaches `runtime_proved`.
- Product-behavior gates:
  `scripts/validate_v9_product_behavior.py` plus the two minimal CLI product-path checks below prove clarification routing, execution-aware summaries, recovery guidance, HPC handoff quality, and explicit refusal behavior.
- Structure/coherence gates:
  `python -m unittest`, `scripts/validate_backend_execution.py`, `scripts/validate_supported_workflows.py`, `scripts/validate_v11_task_suite.py`, and `scripts/refresh_goal_audit.py` prove contract stability, backend/fallback accounting, supported-workflow artifact coherence, natural-language task-suite behavior, and evidence aggregation.
- Not a local runtime-proof gate:
  none of the commands above prove that this workstation can numerically run PyQUDA end to end. They prove grounded generation and auditable probe/runtime reporting, not local `runtime_proved`.

Minimal product-path checks:

```bash
PYTHONPATH=src $PYTHON_BIN -m pyquda_agent.cli run "please compute the pion two-point correlator" --backend auto --no-interactive --result-format terminal --output outputs/v9_rough_check.py --pyquda-repo ~/PyQUDA
PYTHONPATH=src $PYTHON_BIN -m pyquda_agent.cli run "please compute the pion two-point correlator from gauge ~/PyQUDA/tests/weak_field.lime lattice size 4 4 4 8 grid 1 1 1 1 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed source timeslice 0 outputs/v9_pion.npy outputs/v9_pion.py resource_path=.cache/quda cluster_launch=local" --backend auto --no-interactive --result-format terminal --runtime-probe --probe-timeout 5 --output outputs/v9_pion.py --pyquda-repo ~/PyQUDA
```

Artifact boundary for the v9 closeout:

- `data/backend_execution.json`
  Proves the real CLI backend interpretation path, fallback categories, backend-selection behavior, and rough-request lifecycle coherence across `auto` / `api` / `codex`.
  It does not prove supported-workflow script generation or local numerical execution.
- `data/supported_workflows_validation.json`
  Proves that each supported workflow family routes coherently from rough and direct requests into grounded artifacts, generated scripts, and probe-status reporting for the current `11` families / `17` grounded targets.
  It also records a compact `hpc_handoff` coherence summary, including gauge-entry vs propagator-entry counts and the normalized input/output directory policy split across the current supported catalog.
  It is intentionally limited to supported paths; unsupported nearest-grounded recovery actions are summarized in `data/v9_product_behavior.json`.
  A coherent direct run may still end in `generated_runtime_blocked` because the runtime environment is incomplete or because the explicit generated-script probe surfaced a concrete blocker before reaching `runtime_proved`.
  It does not prove that this workstation reaches `runtime_proved`.
- `data/v9_product_behavior.json`
  Proves the product-facing regression surface: clarification behavior, terminal rendering, backend/runtime recovery guidance, explicit unsupported refusal, and probe-artifact consistency.
  It is the source of truth for unsupported-action contracts such as `retry_supported_workflow` versus `choose_supported_variant`.
  It does not replace the structure/coherence validators or prove local runtime success.
- `data/v11_task_suite.json`
  Proves the current task-suite contract for realistic natural-language requests, including candidate-target previews, formula/workflow previews, clarification-vs-unsupported behavior, and nearest-grounded recovery expectations.
  It is intentionally a behavior audit, not proof that the current machine can execute PyQUDA numerically.
- `data/v12_execution_readiness.json`
  Answers the v12 closeout questions directly: whether at least one backend is currently usable, whether runtime evidence is stronger than v11, and whether high-value rough tasks now land in clarification/recovery paths instead of manual-fallback-first responses.
  It also proves that backend degradation still yields repair contracts and that runtime blockers are separated into dependency, probe-harness, input-visibility, output-writability, and cluster-assumption classes.
  It does not replace full supported-workflow validation or prove local `runtime_proved`.

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
