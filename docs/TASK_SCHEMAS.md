# Task Schemas

## Workflow families

Current runnable implementation set supports seventeen concrete workflow targets across eleven workflow families:

- `pion_2pt_chroma_wall_local_zero_momentum_npy_v1`
- `pion_2pt_existing_propagator_local_zero_momentum_npy_v1`
- `pion_pcac_chroma_wall_local_zero_momentum_npy_v1`
- `pion_pcac_existing_propagator_local_zero_momentum_npy_v1`
- `pion_dispersion_chroma_point_momentum_npy_v1`
- `meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1`
- `meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1`
- `proton_2pt_chroma_wall_local_zero_momentum_npy_v1`
- `proton_2pt_existing_propagator_local_zero_momentum_npy_v1`
- `rho_vector_chroma_wall_local_zero_momentum_npy_v1`
- `rho_vector_existing_propagator_local_zero_momentum_npy_v1`
- `quark_propagator_chroma_point_hdf5_v1`
- `quark_propagator_gaussian_shell_chroma_hdf5_v1`
- `ape_smear_chroma_qio_npy_v1`
- `hyp_smear_chroma_qio_npy_v1`
- `stout_smear_chroma_qio_npy_v1`
- `wilson_flow_chroma_qio_energy_npy_v1`

The supported flow is:

`natural language request -> physics interpretation -> clarification loop -> workflow match -> structured task spec -> reference-grounded implementation plan -> complete script -> minimal validation`

The implementation targets remain intentionally narrow so complete mode does not collapse into pseudocode, but the system-level parser and intent layer are no longer hard-coded to a single workflow.

## Physics artifact

Each run now writes `*.physics.json` before any complete generation. It records:

- `user_request`
- `normalized_request`
- `candidate_targets`
- `inferred_interpretation`
- `confirmed_interpretation`
- `formula_proposals`
- `inherited_fields`
- `user_confirmed_fields`
- `inferred_fields`
- `clarified_fields`
- `parser_guesses`
- `fixed_by_workflow_fields`
- `unsupported_fields`
- `chosen_workflow_target`
- `local_references`
- `external_citations`
- `llm_assistance`
- `knowledge_boundary`

### Draft fields

- `user_request`
- `task_type`
- `workflow_id`
- `start_from`
- `has_existing_propagators`
- `gauge_format`
- `gauge_path`
- `propagator_format`
- `propagator_paths`
- `lattice_size`
- `grid_size`
- `fermion_action`
- `mass`
- `xi_0`
- `nu`
- `coeff_t`
- `coeff_r`
- `solver_tol`
- `solver_maxiter`
- `multigrid_blocks`
- `stout_smear_steps`
- `stout_smear_rho`
- `stout_smear_ndim`
- `flow_steps`
- `flow_epsilon`
- `source_type`
- `sink_type`
- `gamma_insertions`
- `momentum_projection`
- `momenta`
- `source_timeslices`
- `gauge_fixed`
- `correlator_output_format`
- `correlator_output_path`
- `resource_path`
- `cluster_launch`
- `script_output_path`
- `script_style`
- `notes`
- `missing_fields`
- `unsupported_reasons`
- `field_sources`
- `inherited_fields`
- `user_confirmed_fields`
- `inferred_fields`
- `clarified_fields`
- `parser_guesses`
- `fixed_fields`
- `unsupported_fields`
- `chosen_workflow_target`
- `pyquda_references`
- `external_citations`

### Resolution model

- The intent interpreter first produces a physics-target artifact.
- If an `api` or `codex` backend is actually available, it may assist with rough-request normalization, uncertain target interpretation, and ambiguous formula/operator explanation.
- If the selected backend is unavailable or fails, the physics artifact records an explicit rule-based fallback under `llm_assistance`; it does not pretend an LLM call succeeded.
- `llm_assistance` also records the resolved backend path or API model/provider details when available, plus a machine-readable fallback category such as `local_executable_missing`, `authentication_error`, `network_error`, `rate_limited`, or `upstream_service_error`.
- Physics clarification must confirm the target before workflow matching.
- The workflow matcher either selects the supported runnable target or returns explicit unsupported reasons.
- Current supported workflow families are:
  - `pion_2pt`: zero-momentum pion two-point from gauge with a wall source, plus the grounded existing-propagator entry path
  - `pion_pcac`: zero-momentum PCAC pion correlator from gauge, plus the grounded existing-propagator entry path
  - `pion_dispersion`: point-source pion dispersion with the fixed local momentum list
  - `meson_spec`: fixed meson spectroscopy from gauge or existing wall-source propagators with gamma5/gamma4gamma5 insertions and the grounded `|p|^2<=9` momentum family
  - `proton_2pt`: zero-momentum proton two-point from gauge or existing wall-source propagators using the local `3_Pion_Proton_2pt.py` contraction path
  - `rho_vector`: zero-momentum rho/vector two-point from gauge or existing wall-source propagators with wall source, local sink, and the fixed spatial gamma_i insertion family
  - `quark_propagator`: point-source and gaussian-shell quark propagator generation from gauge with grounded HDF5 output and fixed local setup constraints
  - `ape_smear`: gauge smearing through the grounded APE helper path
  - `hyp_smear`: gauge smearing through the grounded HYP helper path
  - `stout_smear`: gauge smearing through the narrow `readQIOGauge -> gauge.copy() -> stoutSmear(1, 0.241, 3) -> writeNPYGauge` path
  - `wilson_flow`: Wilson-flow energy-history generation from gauge with `wilsonFlowChroma(flow_steps, flow_epsilon)` and `.npy` output
- Only after a successful match does the task clarifier ask for missing implementation/runtime fields.
- Session reuse is conservative: inherited values are only applied when the current request has not already supplied that field.
- When a run is resumed from a saved session, the next clarification batch can also reuse the previous `minimal_missing_fields` order so the user is not forced into a freshly reshuffled question set each turn.
- Resumed sessions may also reuse backend memory in `auto` mode. The artifact distinguishes `session_backend_memory_considered` from `session_backend_memory_used`, so a caller can see whether the remembered backend degradation merely influenced selection or actually led to a successful alternative backend path.
- A few low-risk runtime assumptions are defaulted instead of re-asked every time: `resource_path=.cache/quda` and `cluster_launch=local` when the request does not specify them. These still remain explicit in artifacts through `field_sources=default`.
- The implementation plan records:
  - `user_request`
  - `inferred_interpretation`
  - `confirmed_interpretation`
  - `workflow_match`
  - `physics_choices`
  - `pyquda_choices`
  - `runtime_choices`
  - `runtime_readiness`
  - `field_resolution`
  - `convention_decisions`
  - `clarification_trace`
  - `references`
- Complete generation is allowed only when all required fields are resolved and the request stays inside the fixed v1 scope.

### Clarification order

The system now asks questions in this order:

1. confirm the physics target and operator/channel intent
2. ask the minimal physics-level task questions needed to choose a family, such as `start_from`, `source_timeslices`, and `gauge_fixed`
3. map the confirmed target to a supported workflow
4. ask only the remaining implementation fields
5. ask the remaining runtime/path/cluster fields
6. stop with `needs_input` or `unsupported` if the target is still unclear or outside current support

Within each stage, questions are further prioritized by branching impact:

- physics ambiguity first
- family-selection blockers second
- complete-generation blockers third
- lower-value runtime conveniences last

### Intermediate artifacts

For an output script such as `outputs/run_pion.py`, the CLI also writes:

- `outputs/run_pion.physics.json`
- `outputs/run_pion.task.json`
- `outputs/run_pion.plan.json`
- `outputs/run_pion.probe.json` when `--runtime-probe` is enabled

`outputs/run_pion.physics.json` captures the inferred physics interpretation, formula/operator proposals, and confirmation status.
It also records whether an LLM backend was actually used or whether the run fell back to rules, plus the current knowledge boundary:

- local curated citation JSON is implemented
- model inference may be used
- live online lookup is opt-in and only attempted for underspecified meson-like requests
- live online lookup currently enriches formula/operator proposals and provenance; it does not auto-confirm a supported workflow
- legacy `true_online_lookup` remains in the artifact only as a compatibility note

`outputs/run_pion.task.json` captures the parsed and clarified task fields.
It also distinguishes inherited session facts from newly clarified or user-specified fields.

`outputs/run_pion.plan.json` captures references, convention decisions, runtime readiness, and the validation contract for complete generation.
It also records `inherited_session_fields` when resumed-session reuse affected the current run.
For resumed-session backend routing, the same artifact chain may also record `llm_session_backend_memory_considered`, `llm_session_backend_memory_used`, and `llm_session_backend_prior_category`, which keep “memory influenced backend choice” distinct from “memory led to a successful alternative backend call.”
`field_resolution` keeps the flat per-field source map and also adds `_resolution_buckets` / `_physics_resolution_buckets` so inherited, clarified, inferred, parser-guessed, and workflow-fixed fields remain auditable.

`runtime_readiness` now includes `evidence_levels` with:

- `syntax_valid`
- `structurally_grounded`
- `runtime_ready`
- `runtime_proved`
- `current_level`
- `blockers`

It also records:

- `probe_policy` to make it explicit that generated scripts are not auto-executed during normal `run`
- `generated_script_path` / `generated_script_exists`
- `generated_script_probe.command` and `generated_script_probe.artifact_path` for explicit follow-up proof
- `artifact_chain` so the runtime evidence stays tied to the sibling `*.physics.json`, `*.task.json`, and `*.plan.json`

When `--runtime-probe` is enabled, the CLI result also distinguishes:

- generation success under top-level `status`
- execution/probe outcome under top-level `execution_status`
- raw probe payload under top-level `probe`

The top-level CLI JSON now also includes `result_summary`, a compact review-oriented summary that surfaces:

- `schema_family` and `schema_version` so thin clients can treat the summary as a versioned product-facing contract
- current `status`
- resolved `physics_target`
- matched `workflow_target`
- requested vs selected backend
- whether LLM assistance was attempted/used and, when it fell back, the `llm_fallback_category` / `llm_fallback_reason`
- `backend_diagnostic`, a user-facing interpretation of backend status that preserves the raw fallback category but also provides a clearer `next_step` and `recommended_fix`
  this now also covers finer API/backend failure classes such as `endpoint_not_found`, `request_error`, `response_parse_error`, and `empty_response`
  and it adds `failure_origin`, `recovery_mode`, and `retryable_now` so thin clients can distinguish local configuration problems from credentials, network, upstream-service, or backend-response failures
- `execution_status` / runtime level when present
- `generation_result`, a thin generation-only outcome card with:
  `phase`, `headline`, `ready`, `emitted`, `succeeded`, `script_path`, and `script_exists`
- `execution_result`, a thin execution/probe outcome card with:
  `phase`, `headline`, `attempted`, `succeeded`, `runtime_probe_status`, `runtime_level`, `evidence_level`, `probe_available`, `blocked`, `probe_command`, and `probe_artifact`
- `execution_closure`, a more direct execution-aware product card with:
  `state`, `headline`, `generation_phase`, `execution_phase`, `runtime_category`, `backend_category`, `why`, `next_artifact`, `next_command_kind`, `next_command`, `probe_artifact`, `script_artifact`, and `actionable`
  this is the shortest stable answer to "are we blocked on clarification, generation, missing runtime environment, probe harness failure, or already runtime-proved?"
- `execution_checkpoint`, an even thinner product checkpoint card with:
  `state`, `headline`, `generation_phase`, `execution_phase`, `runtime_probe_status`, `runtime_level`, `diagnostic_category`, `generated_script_exists`, `probe_artifact`, `probe_command`, `hpc_handoff_ready`, `next_artifact`, `next_action_kind`, and `next_action_command`
  this is the shortest stable answer to "is the run still clarifying, already generated but not probed, blocked by runtime environment, blocked by the probe harness, or ready for handoff/runtime proof?"
- a short preview of missing fields or pending clarification questions
  when the run is blocked on physics-target confirmation, this preview now also surfaces `confirmed_target_id` so `needs_input` does not appear to have zero missing fields
  and when task clarification is already in progress, the preview follows the current clarification priority rather than the raw schema field order
- a more concrete `next_action` string that can inline the first pending prompt, an example answer, and a short current-batch field summary
- `pending_question_prompts` / `pending_question_categories` so summary-only output still tells the user what to answer next
- `pending_question_preview` as a structured summary of the next few clarification items, including `prompt`, `answer_kind`, `answer_example`, and `set_example`
- `clarification_gap_summary`, which groups the current clarification batch by `physics`, `implementation`, and `runtime` so a matched-but-incomplete run says what is still missing in user-facing terms instead of only listing raw field names
- `clarification_batch_card`, which turns the current `needs_input` round into a reviewable task-clarification card:
  the raw current batch fields,
  the expanded display coverage after stable grouped subsets such as `clover_solver_parameters` are taken into account,
  how many fields remain after this batch,
  whether grouped `--set ...` continuation is available,
  and whether the next milestone after this batch is more clarification or complete generation
- `clarification_status`, a compact machine-readable clarification batch object that records:
  whether clarification is active,
  whether the current round is physics confirmation or task-field collection,
  the full current question batch,
  whether the preview is truncated,
  and whether `reply` or `set` is the recommended continuation mode
- `clarification_status.field_groups` can also expose stable grouped subsets inside a batch, such as the current `clover_solver_parameters` group for `mass/xi_0/nu/coeff_t/coeff_r/solver_tol/solver_maxiter`
- another current grouped subset is `lattice_geometry` for `lattice_size/grid_size`
- when a stable grouped subset is relevant to the current batch, `recommended_answer_mode` may now prefer `set`, and `action_queue` / `primary_action` can surface that grouped `--set ...` path first
- when a stable grouped subset dominates the current round, the batcher preserves the complete group instead of truncating it mid-group, so grouped `--set ...` continuations stay reviewable and copyable
- `pending_group_set_examples` can expose copyable grouped `--set ...` shorthands whenever a stable grouped continuation is available for the current batch, even if a few non-group fields still need explicit `--set field=value`
- `pending_set_examples` for copyable individual `--set ...` tokens that match the current clarification priority
- `pending_reply_examples` for copyable `--reply ...` tokens when you want to answer by order instead of by internal field name
- a more concrete `set_hint` that prefers the currently prioritized clarification questions and uses example values when the field shape is known
- `reply_hint` for a field-name-free continuation command that replays the next few pending answers in order
- the preview lists stay capped for readability, but `set_hint` / `reply_hint` may cover the full current question batch so one continuation command can often clear the whole round
- `action_queue`, an ordered list of the most actionable next commands or fixes so terminal users do not need to infer priority from several separate hint fields
- clarification-related actions now include the current batch fields in their title/guidance so clients can render a useful next-step label directly
- `primary_action`, a shortcut for the first queue item when a client only wants the single best next step
- `run_overview`, a compact UI-facing summary that condenses the current phase, headline, blocking kind, backend state, runtime level, and primary action identity
- `blocking_reason`, a one-line explanation of why the current run is blocked, degraded, or explicitly using fallback
- `blocking_reason_detail`, a structured companion for `blocking_reason` with stable fields such as `category`, `source`, and optional backend/runtime subtype keys
  when a precise backend/runtime subtype is known, this can distinguish categories such as `backend_configuration_missing`, `backend_credentials_missing`, `backend_network_error`, `backend_timeout`, `backend_endpoint_not_found`, `backend_request_error`, `backend_response_parse_error`, `backend_empty_response`, `runtime_dependencies_missing`, `runtime_probe_harness_failed`, or `unsupported_request`
  otherwise it falls back to a broader category such as `backend_fallback`
- `inspection_hint`, a structured first-artifact pointer with `label`, `artifact_key`, and `path`, so clients can surface the most useful file to open next without recomputing it from run state
- `frontend_profile`, a compact frontend-ready profile that condenses:
  a status card,
  a minimal capability card,
  the primary next action,
  and the first artifact to inspect,
  while reusing the same underlying summary semantics rather than defining a second lifecycle model
- `backend_path`, a thinner backend-outcome record with:
  `requested_backend`, `selected_backend`, `status`, `category`, `failure_origin`, `recovery_mode`, `retryable_now`, `current_result_usable`, `continue_with_current_result`, and the current backend-repair action fields
- `hpc_handoff`, a concise submission/handoff record with:
  `cluster_launch`, `resource_path`, `start_from`, `input_paths`, `input_manifest`, `input_path_count`, `input_directories`, `input_directory_policy`, `input_mutability_policy`, `output_paths`, `output_directories`, `output_directory_count`, `output_directory_policy`, `output_input_overlap_forbidden`, `input_visibility`, `output_writer_policy`, `required_modules`, `preflight_checks`, `submission_assumption`, `handoff_boundary`, `runtime_level`, `generated_script_exists`, `probe_artifact`, and `probe_command`
- each action item now includes `actionable` so clients can distinguish copyable commands from guidance-only steps
- each action item also includes `action_state`:
  `ready` for directly runnable steps,
  `conditional` for partial retry commands that may still need setup,
  `blocked` when the user must satisfy a prerequisite before retrying
- when `actionable` is `false`, `actionability_reason` explains which prerequisite is still missing
- continuation hints preserve the current run mode where possible, including backend choice and flags such as `--dry-run`, `--no-interactive`, and summary output mode

For the current product-facing taxonomy, see `docs/RESULT_SUMMARY_TAXONOMY.md`.
When the full CLI payload is requested, the most stable product-facing summary fields are also mirrored back to the top level for convenience, including `run_overview`, `capability_summary`, `blocking_reason`, `blocking_reason_detail`, `inspection_hint`, and `frontend_profile`.

The full `context` payload also now includes `index_provenance`:

- `matched` means the loaded local index was built for the same PyQUDA repo as the current `--pyquda-repo`
- `repo_mismatch` means the stored `index_summary` comes from another checkout, so snippets and explicit file paths should be treated as the primary grounding unless the index is refreshed
- `unknown` means the index artifact did not record enough repo-root metadata to verify the match

The compact `result_summary` mirrors the same `index_provenance` object so summary-only clients can still detect mismatched index artifacts without requesting the full `context`.
- continuation hints also preserve an explicit `--llm-timeout` when you use one to keep backend-assisted runs bounded
- the key artifact paths in review order

If you want the CLI to print only this compact object for interactive terminal use, run with `--summary-only` or `--result-format summary`.
The backend-facing intent prompt is compact too: it uses a reduced rule-based physics snapshot with counts for local references and curated citations rather than embedding the full citation records or full local-reference lists directly in the LLM request.
For clearly identified rough requests, that first backend prompt also omits detailed formula/operator proposal payloads and keeps that extra detail for ambiguous interpretation cases.
For local `codex`, a rough request with one strong unconfirmed rule-based target may now use a normalization-only first stage instead of a full interpretation rewrite; this is exposed as `llm_intent_strategy=normalization_only` together with `llm_intent_prompt_profile`.
For explicit `--backend codex` on that same path, the summary may also record `llm_codex_preflight_skipped` / `llm_codex_preflight_skip_reason`, which means the run skipped the extra codex preflight and used the real codex call as the first backend signal.
If that exact normalization-only codex stage times out, the same summary may record `llm_timeout_recovery_skipped` and `llm_timeout_recovery_skip_reason` instead of attempting a second low-value retry against the same tiny prompt shape.
When backend-assisted intent interpretation hits a timeout, the same path may also record a single bounded timeout-recovery retry through `llm_timeout_recovery_attempted`, `llm_timeout_recovery_used`, `llm_timeout_recovery_failed`, and related fields, so clients can distinguish “one timeout then recovery succeeded” from “timeout and final fallback”.
For local `codex`, the same summary may also expose `llm_intent_primary_timeout_seconds`, which records the shorter cap used for the first intent-interpretation attempt before timeout recovery is considered. The rough `normalization_only` codex path may use a smaller value than the heavier full-interpretation path.
The same summary may also include:

- `product_status`, a single product-facing lifecycle label such as:
  `needs_input`,
  `ready_to_generate`,
  `generated_probe_available`,
  `generated_runtime_blocked`,
  `runtime_proved`,
  or `unsupported`
- `artifacts.session` for the default or explicit session state file
- `resume_hint` for the next `run --resume-session ...` command when continuation is useful
- `set_hint` for a shorter continuation command that also demonstrates `--set field=value`
- `group_set_hint` for a shorter continuation command that uses grouped `--set` shorthands when available, for example `--set clover_solver_parameters=0.09253,4.8965,...,1000`
- current grouped shorthands also include `--set lattice_geometry=24,24,24,72;1,1,1,2`
- `probe_hint` after successful generation so runtime proof can be retried from the CLI without opening nested `runtime_evidence`
- `workflow_outcome`, a unified status view that distinguishes:
  generation blocked on clarification,
  dry-run ready,
  generated without probe,
  generated and probe-attempted,
  plus `runtime_probe_status`, current evidence level, blockers, and the recommended next command
- when probe execution infrastructure itself fails, `execution_status` / `runtime_probe_status` may also be `probe_driver_failed`; this still means script generation succeeded and the emitted `*.probe.json` artifact should be reviewed for the harness-side blocker
- `supported_workflows`, the current explicit workflow-family catalog exposed directly in the result payload
- `nearby_supported_workflows`, a smaller subset chosen from that catalog when the request is unsupported, so callers can point the user to the nearest grounded implementation families instead of only repeating a generic refusal
- `physics_workflow_preview`, which maps the current candidate physics targets onto the currently grounded workflow targets, so ambiguous requests can be reviewed as `candidate formula/operator choice -> runnable family` instead of only as a free-form interpretation
- `unsupported_guidance`, an additive refusal card that extracts the primary conflict, preserves the full unsupported reasons, and attaches adjustment hints for the nearest supported workflow families
- `unsupported_guidance.primary_scope`, which classifies the nearest grounded mismatch as `physics`, `implementation`, or `runtime`
- `unsupported_guidance.shortest_fix.scope_breakdown`, which groups the minimum user-side changes by the same three scopes
- `unsupported_guidance.shortest_fix_gap_summary`, which turns that scope breakdown into a user-facing sentence plus ordered scope items
- `unsupported_guidance.nearest_workflow_card`, which promotes the nearest grounded workflow, required change count, and grouped missing conditions into one reviewable card
- `unsupported_guidance.retry_suggestions`, which may include:
  a single deterministic retry command when the nearest family has one grounded correction path,
  or a small set of `variant_retry_commands` when the user must still choose among grounded alternatives such as `wall` versus `point`
- explicit physics targets may also be `confirmed` yet still unsupported, for example when the request clearly names a target such as `neutron two-point correlator` that the current grounded local workflow catalog can explain at the formula/operator level but cannot implement as a runnable PyQUDA family yet
- in that case the refusal path should still preserve `physics_formula_preview`, keep provenance explicit, and make the nearest grounded workflow switch visible inside `unsupported_guidance.shortest_fix` instead of collapsing back to a generic baryon clarification
- `delivery_status`, a compact product-facing split between:
  generation status,
  execution/probe status,
  and the current primary next step,
  so clients can distinguish generation success from runtime-proof success without recombining top-level fields manually
- `runtime_diagnostic`, a smaller runtime-focused diagnosis that distinguishes:
  `probe_available`,
  `runtime_missing`,
  `probe_driver_failed`,
  and `runtime_proved`,
  so clients can tell whether to fix the runtime environment or the probe harness itself
- `capability_summary`, a compact three-part card for:
  backend capability state,
  generation capability state,
  and runtime-evidence state,
  so product-facing clients can render one direct status block without recomputing it from `workflow_outcome`, `delivery_status`, and `backend_diagnostic`
- `terminal_message`, a terminal-facing distilled message with:
  `headline`,
  `detail`,
  `recommended_command`,
  and `alternative_commands`,
  so `summary-only` consumers can show one human-readable conclusion without recomputing it from the rest of the payload
  and `--result-format terminal` can render a stable `Outcome / Detail / Status / Artifacts / Command / Options` card directly from the same data
- `backend_selection_reason` plus `llm_codex_preflight_*` fields, which explain why `--backend auto` used local codex, switched to API, or fell back to rules

For backend provenance beyond a single run, `data/backend_execution.json` records whether `auto`, `api`, or `codex` were used successfully in the real CLI path or whether they fell back explicitly with reason/category metadata.
It now also summarizes each backend with an `availability_state` (`usable`, `mixed`, `fallback_only`, or `incoherent`) and per-case `backend_path` records, including codex soft-preflight metadata when present, so backend reliability can be audited without reading full CLI payloads first.
Those backend-execution case summaries now also keep the product-facing clarification shape visible through `product_status`, `generation_phase`, and `execution_phase`, rather than only backend fallback metadata.
They also preserve `backend_failure_origin`, `backend_recovery_mode`, and `backend_retryable_now`, plus top-level `backend_summary.failure_origin_counts` / `backend_summary.recovery_mode_counts` so validation consumers can separate local configuration issues from credentials, network, upstream-service, or backend-response problems.
By default this report keeps only compact case summaries plus backend diagnostics; raw `stdout` / `stderr` / parsed CLI payloads are omitted unless the report is regenerated with `--include-raw-payloads`.
