# Run Workflow

`pyquda-agent` keeps `~/PyQUDA` read-only and writes all derived artifacts inside this repository or to an explicit user output path.

Python `>= 3.10` is required for the CLI, validation scripts, and test suite.

Before copying any command below, choose an interpreter that actually reports `>= 3.10`:

```bash
python3 --version
export PYTHON_BIN=python3
```

If that version check prints `< 3.10`, do not keep using bare `python3`. Point `PYTHON_BIN` at an explicit supported interpreter instead:

```bash
export PYTHON_BIN=/path/to/venv/bin/python
$PYTHON_BIN --version
```

All commands below assume `PYTHON_BIN` already points to Python `>= 3.10`. Do not assume a `python3.10` executable exists; use whichever interpreter path is actually available on the machine.

## Primary path

The main path is:

`natural language request -> physics interpretation -> clarification loop -> workflow match -> structured task spec -> reference-grounded implementation plan -> complete script -> minimal validation`

The runnable implementation set is still intentionally narrow. The new part is above it: rough requests are first interpreted at the physics level, then either confirmed and matched to one of the supported workflows, or refused explicitly.

## Refresh analysis artifacts

```bash
$PYTHON_BIN scripts/refresh_pyquda_analysis.py
```

This updates:

- `data/pyquda_index.json`
- `docs/PYQUDA_ARCHITECTURE.md`

## Supported complete workflows

Current supported workflow families and grounded paths:
`11` workflow families / `17` concrete grounded workflow targets.

- family `pion_2pt`
  - `pion_2pt_chroma_wall_local_zero_momentum_npy_v1`
  - `pion_2pt_existing_propagator_local_zero_momentum_npy_v1`
- family `pion_pcac`
  - `pion_pcac_chroma_wall_local_zero_momentum_npy_v1`
  - `pion_pcac_existing_propagator_local_zero_momentum_npy_v1`
- family `pion_dispersion`
  - `pion_dispersion_chroma_point_momentum_npy_v1`
- family `meson_spec`
  - `meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1`
  - `meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1`
- family `proton_2pt`
  - `proton_2pt_chroma_wall_local_zero_momentum_npy_v1`
  - `proton_2pt_existing_propagator_local_zero_momentum_npy_v1`
- family `rho_vector`
  - `rho_vector_chroma_wall_local_zero_momentum_npy_v1`
  - `rho_vector_existing_propagator_local_zero_momentum_npy_v1`
- family `quark_propagator`
  - `quark_propagator_chroma_point_hdf5_v1`
  - `quark_propagator_gaussian_shell_chroma_hdf5_v1`
- family `ape_smear`
  - `ape_smear_chroma_qio_npy_v1`
- family `hyp_smear`
  - `hyp_smear_chroma_qio_npy_v1`
- family `stout_smear`
  - `stout_smear_chroma_qio_npy_v1`
- family `wilson_flow`
  - `wilson_flow_chroma_qio_energy_npy_v1`

Workflow 1: zero-momentum pion two-point

- start from `gauge`
- `chroma_qio` gauge input
- `clover`
- `wall` source
- `local` sink
- zero momentum only
- `.npy` correlator output only

Workflow 1b: zero-momentum pion two-point from existing propagators

- start from `propagator`
- grounded propagator formats only: `npy`, `hdf5`, `chroma_qio`
- `wall` source / `local` sink contract is still fixed
- zero momentum only
- `.npy` correlator output only
- unsupported source/sink/momentum combinations are refused explicitly

Workflow 3: zero-momentum proton two-point

- start from `gauge`
- `chroma_qio` gauge input
- fixed `core.getDirac(...)` path with local multigrid blocks
- fixed stout smear: `steps=1`, `rho=0.125`, `ndim=4`
- `wall` source
- local proton contraction from `examples/3_Pion_Proton_2pt.py`
- zero momentum only

Workflow 6: Wilson-flow energy history

- start from `gauge`
- `chroma_qio` gauge input
- `gauge.copy()`
- `wilsonFlowChroma(flow_steps, flow_epsilon)`
- `.npy` energy-history output only
- no propagator input, no source/sink variants, no momentum projection
- `.npy` correlator output only

Workflow 3b: zero-momentum proton two-point from existing propagators

- start from `propagator`
- grounded propagator formats only: `npy`, `hdf5`, `chroma_qio`
- stored source convention is fixed to `wall`
- fixed local proton contraction from `examples/3_Pion_Proton_2pt.py`
- explicit `source_timeslice` is required for each propagator path so the parity-projected correlator can be aligned correctly
- zero momentum only
- `gauge_fixed=false` only
- `.npy` correlator output only

Workflow 4: fixed meson-spectroscopy correlator family

- start from `gauge`
- `chroma_qio` gauge input
- `clover`
- `wall` source
- `local` sink
- fixed gamma-insertion family:
  - `gamma5_gamma5`
  - `gamma4gamma5_gamma4gamma5`
- non-empty momentum list drawn from the grounded `|p|^2<=9` family in `tests/test_mesonspec.py`
- `.npy` correlator tensor output only
- currently grounded only for `GRID_SIZE[3] == 1`

Workflow 4b: fixed meson-spectroscopy correlator family from existing propagators

- start from `propagator`
- grounded propagator formats only: `npy`, `hdf5`, `chroma_qio`
- stored source convention is fixed to `wall`
- fixed gamma-insertion family:
  - `gamma5_gamma5`
  - `gamma4gamma5_gamma4gamma5`
- explicit `source_timeslice` is required for each propagator path
- non-empty momentum list drawn from the grounded `|p|^2<=9` family in `tests/test_mesonspec.py`
- `gauge_fixed=false` only
- `.npy` correlator tensor output only
- currently grounded only for `GRID_SIZE[3] == 1`

Workflow 5: point-source quark propagator

- start from `gauge`
- `chroma_qio` gauge input
- fixed `core.getDirac(...)` path with local multigrid blocks
- fixed stout smear: `steps=1`, `rho=0.125`, `ndim=4`
- point source fixed at spatial origin `[0, 0, 0]` with one explicit `source_timeslice`
- save one `.h5` / `.hdf5` propagator artifact with `propagator.saveH5(...)`
- no correlator contraction in this family

Workflow 5b: fixed stout-smeared gauge output

- start from `gauge`
- `chroma_qio` gauge input
- `gauge.copy()`
- fixed stout smear: `steps=1`, `rho=0.241`, `ndim=3`
- `io.writeNPYGauge(...)`
- no propagator input, no source/sink variants, no momentum projection
- `.npy` smeared-gauge output only

Workflow 5c: fixed HYP-smeared gauge output

- start from `gauge`
- `chroma_qio` gauge input
- `gauge.copy()`
- fixed HYP smear: `steps=1`, `alpha1=0.75`, `alpha2=0.6`, `alpha3=0.3`, `dir_ignore=4`
- `io.writeNPYGauge(...)`
- no propagator input, no source/sink variants, no momentum projection
- `.npy` smeared-gauge output only

Local scope note:

- `~/PyQUDA/tests/test_smear.py` also shows APE and HYP smear calls.
- The current runnable grounded gauge-smearing families are `ape_smear_chroma_qio_npy_v1`, `hyp_smear_chroma_qio_npy_v1`, and `stout_smear_chroma_qio_npy_v1`.

## Boundary And Expansion Policy

The current product boundary is deliberate:

- rough requests may broaden the clarification front-end, but complete generation stays limited to the grounded workflow catalog above
- unsupported source/sink/momentum/operator combinations must stop at clarification or explicit refusal
- backend fallback or missing runtime proof must remain visible in artifacts and terminal output
- a generated script is only considered complete when it is placeholder-free and traceable to concrete local PyQUDA references

The next safe expansion rule is also deliberate:

1. prefer tightening execution-aware behavior, artifact reviewability, and HPC handoff quality inside existing families
2. only extend a family when the new branch has direct local grounding in `~/PyQUDA/examples`, `~/PyQUDA/tests`, or utilities already indexed by this repository
3. only add a new family when it can match the current standard for clarification behavior, explicit refusal, probe/runtime reporting, and generated-script completeness

This means "broader but shallow" expansions are still out of scope. For example, a generic meson workflow without concrete local grounding is not acceptable just because the front-end can describe it.

Example 1: direct request that maps immediately

```bash
PYTHONPATH=src $PYTHON_BIN -m pyquda_agent.cli run \
  "please compute the pion two-point correlator from gauge ~/PyQUDA/tests/weak_field.lime lattice size 4 4 4 8 grid 1 1 1 1 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed source timeslice 0 outputs/pion.npy outputs/run_pion.py resource_path=.cache/quda cluster_launch=local" \
  --backend codex \
  --no-interactive \
  --output outputs/run_pion.py \
  --pyquda-repo ~/PyQUDA
```

Example 2: rough request that should enter clarification first

```bash
PYTHONPATH=src $PYTHON_BIN -m pyquda_agent.cli run \
  "write a simple PyQUDA script for pi meson two-point from gauge ~/PyQUDA/tests/weak_field.lime outputs/run_pion.py" \
  --backend codex \
  --interactive \
  --output outputs/run_pion.py \
  --pyquda-repo ~/PyQUDA
```

Expected behavior:

1. emit `run_pion.physics.json` with inferred `pion_two_point_correlator`
2. emit `llm_assistance` metadata showing either backend use or explicit fallback
3. ask for confirmation of the physics target
4. after confirmation, ask only the missing implementation/runtime fields
5. write the runnable script only after the workflow matches and all remaining fields are resolved

For rough `meson`-style requests, the physics artifact and clarification prompt now also try to preserve high-value wording from the request itself. In practice this means momentum/dispersion language pushes `pion dispersion` ahead of zero-momentum `pion 2pt` in the candidate list, while plain `meson correlator` wording still keeps the channel/operator unresolved explicitly instead of pretending the pion choice was already confirmed.

For rough `nucleon` / `baryon` requests, the same clarification path now keeps the baryon channel unresolved explicitly and surfaces `proton` plus `neutron` as physics-side candidates. Only `proton` currently maps to a grounded runnable local workflow. A confirmed `neutron` request must stop at explicit `unsupported` with the nearest grounded proton alternatives instead of degrading into a fake neutron script.

For rough `propagator` requests without an explicit hadron channel, the clarification front-end now stays on the quark-propagator family instead of falling back to the meson default. The physics artifact should surface both grounded local branches: `quark_propagator_chroma_point_hdf5_v1` and `quark_propagator_gaussian_shell_chroma_hdf5_v1`. A reply such as `gaussian shell propagator` is expected to carry the branch hint through workflow matching rather than only changing the prompt text.

For requests that already name a supported family but still include explicit uncertainty about the physics/operator branch, the run must stay in physics confirmation rather than jumping ahead to task fields. Current examples are:

- `quark propagator` plus uncertainty about `point` vs `gaussian shell`
- `meson spectrum` plus uncertainty about `gamma5` vs `gamma4gamma5`

In both cases the physics artifact should keep the local grounded candidate formulas visible, and the first question should still be a physics-side confirmation prompt instead of something lower-level like `source_timeslices`.

For rough `hadron correlator` requests, the front-end should now stop one level higher than the old meson-default fallback. The first clarification question must make the user choose at least `meson` versus `baryon`, while still allowing direct confirmation of narrower supported channels such as `pion`, `rho`, or `proton`. The emitted physics artifact should therefore expose both meson-side and baryon-side candidates instead of pretending the request was already meson-like.

The same rule now also applies to mixed-channel wording such as `meson or baryon`, `nucleon or meson`, or `meson spectrum or proton`. Those requests must stay at the hadron-level clarification stage until the user confirms which branch is intended; they must not be silently hijacked by whichever branch-specific keyword happened to be parsed first.

Example 3: direct request for the proton workflow family

```bash
PYTHONPATH=src $PYTHON_BIN -m pyquda_agent.cli run \
  "please compute the proton two-point correlator from gauge ~/PyQUDA/tests/weak_field.lime lattice size 4 4 4 8 grid 1 1 1 1 mass=0.09253 xi_0=1.0 nu=1.0 coeff_t=1.160920226 coeff_r=1.160920226 tol=1e-12 maxiter=1000 source timeslice 0 outputs/proton.npy outputs/run_proton.py resource_path=.cache/quda cluster_launch=local" \
  --backend codex \
  --no-interactive \
  --output outputs/run_proton.py \
  --pyquda-repo ~/PyQUDA
```

Expected behavior: match `proton_2pt_chroma_wall_local_zero_momentum_npy_v1`, emit the three review artifacts, and generate a complete proton script only after the required runtime fields are present.

Example 4: direct request for the pion PCAC workflow family

```bash
PYTHONPATH=src $PYTHON_BIN -m pyquda_agent.cli run \
  "please compute pion pcac ratio from gauge ~/PyQUDA/tests/weak_field.lime lattice size 4 4 4 8 grid 1 1 1 1 mass=-0.2770 xi_0=1.0 nu=1.0 coeff_t=1.160920226 coeff_r=1.160920226 tol=1e-12 maxiter=1000 source timeslice 0 outputs/pion_pcac.npy outputs/run_pion_pcac.py resource_path=.cache/quda cluster_launch=local" \
  --backend codex \
  --no-interactive \
  --output outputs/run_pion_pcac.py \
  --pyquda-repo ~/PyQUDA
```

Expected behavior: match `pion_pcac_chroma_wall_local_zero_momentum_npy_v1`, emit the three review artifacts, and generate a complete PCAC-ratio script grounded in `examples/4_Pion_PCAC.py`.

Example 5: direct request for the dispersion workflow family

```bash
PYTHONPATH=src $PYTHON_BIN -m pyquda_agent.cli run \
  "please compute pion dispersion from gauge ~/PyQUDA/tests/weak_field.lime lattice size 4 4 4 8 grid 1 1 1 1 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 tol=1e-12 maxiter=1000 source timeslice 0 outputs/pion_dispersion.npy outputs/run_pion_dispersion.py resource_path=.cache/quda cluster_launch=local" \
  --backend codex \
  --no-interactive \
  --output outputs/run_pion_dispersion.py \
  --pyquda-repo ~/PyQUDA
```

Expected behavior: match `pion_dispersion_chroma_point_momentum_npy_v1`, emit the three review artifacts, and generate a complete point-source momentum-projected pion script after the required runtime fields are present.

Example 6: direct request for the meson-spectroscopy family

```bash
PYTHONPATH=src $PYTHON_BIN -m pyquda_agent.cli run \
  "please compute meson spectroscopy correlators from gauge ~/PyQUDA/tests/weak_field.lime lattice size 4 4 4 8 grid 1 1 1 1 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 tol=1e-12 maxiter=1000 outputs/meson_spec.npy outputs/run_meson_spec.py resource_path=.cache/quda cluster_launch=local" \
  --backend codex \
  --no-interactive \
  --output outputs/run_meson_spec.py \
  --pyquda-repo ~/PyQUDA
```

Expected behavior: match `meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1`, emit the three review artifacts, and generate a complete wall-source meson-spectroscopy script only inside the grounded gamma/momentum family.

Example 7: direct request for the propagator-entry meson-spectroscopy family

```bash
PYTHONPATH=src $PYTHON_BIN -m pyquda_agent.cli run \
  "please compute meson spectroscopy correlators from existing propagator /tmp/meson_prop_0.npy wall source momentum [0,0,0] momentum [1,1,1] not gauge fixed timeslice 0 lattice size 4 4 4 8 grid 1 1 1 1 outputs/meson_spec_prop.npy outputs/run_meson_spec_prop.py resource_path=.cache/quda cluster_launch=local" \
  --backend codex \
  --no-interactive \
  --output outputs/run_meson_spec_prop.py \
  --pyquda-repo ~/PyQUDA
```

Expected behavior: match `meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1`, emit the three review artifacts, and generate a complete propagator-entry meson-spectroscopy script grounded in `tests/test_mesonspec.py`, `tests/test_io.py`, and `pyquda_utils/io/__init__.py`.

Example 8: direct request for the quark-propagator family

```bash
PYTHONPATH=src $PYTHON_BIN -m pyquda_agent.cli run \
  "please generate a quark propagator from gauge ~/PyQUDA/tests/weak_field.lime lattice size 4 4 4 8 grid 1 1 1 1 mass=-0.2770 xi_0=1.0 nu=1.0 coeff_t=1.160920226 coeff_r=1.160920226 tol=1e-12 maxiter=1000 source timeslice 0 outputs/pt_prop.h5 outputs/run_quark_propagator.py resource_path=.cache/quda cluster_launch=local" \
  --backend codex \
  --no-interactive \
  --output outputs/run_quark_propagator.py \
  --pyquda-repo ~/PyQUDA
```

Expected behavior: match `quark_propagator_chroma_point_hdf5_v1`, emit the three review artifacts, and generate a complete point-source propagator script grounded in `examples/2_Quark_Propagator.py` and `tests/test_io.py`.

## LLM assistance boundary

When configured, `api` / `codex` backends now assist the front-end path for:

- rough request normalization
- uncertain physics-target interpretation
- ambiguous formula/operator explanation

If the selected backend is unavailable or fails, the run falls back to rules and records that explicitly in `physics.llm_assistance`.
The fallback is categorized so local CLI problems, authentication problems, network failures, rate limits, and upstream-service failures are distinguishable in artifacts.
`backend_diagnostic` now also records `failure_origin`, `recovery_mode`, and `retryable_now` so clients can tell whether a run is blocked by local configuration, credentials, network reachability, upstream service state, or incompatible backend responses.
For local `codex`, a rough request with one strong unconfirmed rule-based target now uses a lighter normalization-only first stage instead of always asking codex to restate the whole interpretation. This is recorded in `llm_intent_strategy` / `llm_intent_prompt_profile` and is intended to reduce avoidable rough-request fallback.
For explicit `--backend codex` on that same path, the run now also skips codex preflight and records `llm_codex_preflight_skipped` / `llm_codex_preflight_skip_reason`, because the real codex call is the first meaningful backend signal for that tiny request shape.
If that exact normalization-only codex stage times out, the resolver now skips a second bounded retry and records `llm_timeout_recovery_skipped` / `llm_timeout_recovery_skip_reason`, because a second pass over the same smallest prompt shape is usually just latency without new information.

Current knowledge boundary:

- `data/physics_citations/*.json` are local curated citation artifacts
- model inference may be used for interpretation/proposal text
- `--enable-external-lookup` enables an explicit live online lookup path
- that live path is only attempted for underspecified meson-like requests and currently enriches formula/operator proposals rather than auto-confirming a workflow
- the legacy `true_online_lookup` boundary key remains only as a compatibility marker; the active capability is `live_online_lookup`

Single-command refresh for the default demo artifacts:

```bash
$PYTHON_BIN scripts/refresh_first_workflow_demo.py --pyquda-repo ~/PyQUDA --backend api
```

This command is considered successful when it refreshes the structured artifacts, implementation plan, generated script, backend-parity evidence, and current workflow audit inputs. It does not require the current workstation to have a runnable PyQUDA environment.

To refresh another supported workflow family instead:

```bash
$PYTHON_BIN scripts/refresh_first_workflow_demo.py --pyquda-repo ~/PyQUDA --backend api --workflow pion_pcac
$PYTHON_BIN scripts/refresh_first_workflow_demo.py --pyquda-repo ~/PyQUDA --backend api --workflow pion_dispersion
$PYTHON_BIN scripts/refresh_first_workflow_demo.py --pyquda-repo ~/PyQUDA --backend api --workflow meson_spec
$PYTHON_BIN scripts/refresh_first_workflow_demo.py --pyquda-repo ~/PyQUDA --backend api --workflow proton_2pt
```

Direct backend parity check:

```bash
$PYTHON_BIN scripts/check_backend_parity.py --pyquda-repo ~/PyQUDA
$PYTHON_BIN scripts/check_backend_parity.py --pyquda-repo ~/PyQUDA --workflow pion_pcac
$PYTHON_BIN scripts/check_backend_parity.py --pyquda-repo ~/PyQUDA --workflow pion_dispersion
$PYTHON_BIN scripts/check_backend_parity.py --pyquda-repo ~/PyQUDA --workflow meson_spec
$PYTHON_BIN scripts/check_backend_parity.py --pyquda-repo ~/PyQUDA --workflow proton_2pt
```

Integration-style validation for all supported workflow families:

```bash
$PYTHON_BIN scripts/validate_supported_workflows.py --pyquda-repo ~/PyQUDA --backend codex
```

Real backend execution validation for the front-end interpretation path:

```bash
$PYTHON_BIN scripts/validate_backend_execution.py --pyquda-repo ~/PyQUDA
```

The resulting `data/backend_execution.json` now includes a compact per-backend `availability_state` such as `usable`, `mixed`, `fallback_only`, or `incoherent`, including the default `auto` entry in addition to explicit `api` / `codex`, plus per-case `backend_path` summaries with requested backend, selected backend, selection reason, fallback category, intent strategy/prompt profile, timeout-recovery skip/use state, and codex preflight diagnostics when relevant.
It now also includes backend failure-origin and recovery summaries, both per case and as top-level aggregate counts, so product clients can tell whether real runs mostly fail because of local configuration, credentials, network, upstream service state, or incompatible backend responses.
It now also audits the rough-request product path directly, requiring coherent `product_status`, `generation_result.phase`, and `execution_result.phase` values for the clarification-stage runs.
The default report is intentionally compact: it keeps case summaries and backend diagnostics, while raw CLI `stdout` / `stderr` / parsed payloads are only retained if you rerun the validator with `--include-raw-payloads`.

The supported-workflow validation report now also keeps a compact backend summary for both the rough and direct request path of each workflow, so routing/runtime coherence and backend-degradation semantics stay visible in one artifact.
It now also records a compact `hpc_handoff` coherence summary for the whole supported catalog, including the current gauge-entry vs propagator-entry split and the normalized input/output directory-policy counts across the `11` families / `17` targets.
For the current supported complete workflows, the generated scripts also keep an explicit HPC handoff contract near the top of the file and in `_validate_handoff_contract()` / `_print_handoff_summary()`. That contract now includes the launch assumption, grounded gauge/source/sink family constraints, QUDA resource-path assumption, sibling artifact expectations, and stricter preflight checks for lattice/grid divisibility plus workflow-specific fixed parameters such as momentum lists, multigrid blocks, or stout-smear settings.

Optional local interpreter scan for an already-usable PyQUDA runtime:

```bash
$PYTHON_BIN scripts/scan_runtime_candidates.py --pyquda-repo ~/PyQUDA
```

If you explicitly want local execution proof and the scan still reports no ready interpreter, use
[PYQUDA_RUNTIME_BOOTSTRAP.md](/Users/zhaodianjun/pyquda-agent/docs/PYQUDA_RUNTIME_BOOTSTRAP.md)
to align the Python environment with the upstream PyQUDA install/development paths already present on this machine.

Useful flags:

- `--dry-run`: stop after task spec, retrieval, and implementation plan
- `--no-interactive`: do not ask follow-up questions; return missing fields instead
- `--print-context`: print the retrieval bundle used for generation
- `--save-session state.json`: persist the structured task draft
- `--resume-session state.json`: continue from a saved draft
- `--set field=value`: apply one clarification answer directly in non-interactive mode; repeat as needed

Even without `--save-session`, the current run path now writes a sibling default session artifact such as `outputs/run_pion.session.json`.
When a run ends in `needs_input` or `dry_run`, the CLI result also includes `resume_hint`, `reply_hint`, and `set_hint` so the next command can be copied directly, either by pending-question order (`--reply ...`) or by explicit field update (`--set field=value`).
When a saved session already had a clear pending batch, the resumed run now tries to preserve that batch order instead of immediately reshuffling to a new global priority order.
When a resumed session records that a prior codex path degraded in a low-value way, `--backend auto` can now prefer a configured API backend immediately instead of repeating the same local codex attempt first. This currently applies to remembered codex timeout, authentication, local-environment, backend-process, and missing-executable failures, and the reason is written into both `llm_assistance.selection_reason` and `backend_diagnostic`.
The current run path also defaults a couple of low-risk runtime assumptions when they are omitted: `resource_path=.cache/quda` and `cluster_launch=local`. They are still written explicitly into artifacts, but they no longer consume a clarification slot by default.
The summary previews remain short on purpose, but the continuation hints now try to cover the full current clarification batch so one copied command is more likely to unblock the next stage completely.
`next_action` now also carries a short current-batch field summary in addition to the first prompt/example, so summary-only users can see at a glance what this round is trying to resolve.
For UI clients, the same summary now also exposes `clarification_status`, which reports the full current question batch, whether the visible preview is truncated, and whether `reply` or `set` is the preferred continuation mode.
The clarification `action_queue` entries now also embed that batch context directly in their title/guidance, so clients can surface the preferred next step without stitching together separate fields first.
When a clarification round aligns with a stable parameter cluster, `clarification_status.field_groups` and the clarification action titles can also surface that grouping directly, for example `clover solver parameters`.
When a stable grouped subset is relevant, the summary can now prefer grouped `--set ...` continuation directly through `recommended_answer_mode=set`, so parameter-heavy rounds do not default to long ordered `--reply ...` chains.
If a stable grouped subset dominates the current batch, the clarifier now keeps the full group together instead of cutting the batch in the middle of that group.
For the current `clover solver parameters` path, the summary can emit a shorter grouped continuation through `pending_group_set_examples` / `group_set_hint`, using `--set clover_solver_parameters=...` in the fixed field order, plus any remaining explicit `--set` fields needed for this round.
Concrete grouped example:
`--resume-session outputs/run_pion.session.json --set clover_solver_parameters=0.09253,4.8965,0.86679,0.8549165664,2.32582045,1e-12,1000`
Geometry batches now also support:
`--resume-session outputs/run_pion.session.json --set lattice_geometry=24,24,24,72;1,1,1,2`
For `dry_run`, `resume_hint` preserves the current run mode exactly, but the `generate_script` action exposed through `action_queue` and `primary_action` strips `--dry-run` so the suggested primary command actually emits the script.
Relative script/data paths mentioned in the request are resolved under the current runtime output root, so a request like `outputs/run_pion.py` stays under the chosen run directory instead of jumping to an unrelated parent path.

Session reuse in the current run path is conservative:

- previously confirmed fields may be inherited when the new request does not explicitly override them
- inherited values are marked as `field_sources=inherit`-style session reuse in artifacts rather than being mixed into user-confirmed fields
- previously confirmed physics targets are only reused when the new request is still ambiguous

Generated intermediate artifacts:

- `outputs/run_pion.physics.json`
- `outputs/run_pion.task.json`
- `outputs/run_pion.plan.json`
- `outputs/run_pion.py`

The refreshed demo script also produces a rough-request preview artifact set before the final complete script generation:

- `outputs/run_pion_api_rough.physics.json`
- `outputs/run_pion_api_rough.task.json`
- `outputs/run_pion_api_rough.plan.json`

The script is the last artifact in the chain, not the first one to review. If required fields are missing, complete mode must stop at `needs_input` or `unsupported` instead of emitting template-style code.

For HPC handoff, the generated script now also embeds:

- launch assumption text
- input/output filesystem contract
- sibling `physics.json` / `task.json` / `plan.json` expectations
- lattice/grid divisibility checks
- source-timeslice bounds checks
- early path/suffix validation before any PyQUDA initialization

Review order should follow the same pipeline:

1. inspect `*.physics.json`
2. inspect `*.task.json`
3. inspect `*.plan.json`
4. inspect the generated script

## Minimal validation

Repository-level success means grounded script generation plus auditable runtime/probe status. It does not automatically mean that the current workstation is already `runtime_proved` for PyQUDA execution.

Recommended local checks:

```bash
$PYTHON_BIN -B -m unittest
$PYTHON_BIN scripts/validate_backend_execution.py --pyquda-repo ~/PyQUDA
$PYTHON_BIN scripts/validate_supported_workflows.py --pyquda-repo ~/PyQUDA --backend codex
$PYTHON_BIN scripts/validate_v9_product_behavior.py
$PYTHON_BIN scripts/validate_v11_task_suite.py
$PYTHON_BIN scripts/refresh_goal_audit.py
```

If you want the full artifact refresh chain as well:

```bash
$PYTHON_BIN scripts/refresh_pyquda_analysis.py
$PYTHON_BIN scripts/refresh_physics_citations.py
$PYTHON_BIN scripts/refresh_first_workflow_demo.py --pyquda-repo ~/PyQUDA --backend api
```

The dedicated v9 product-behavior validator writes a grouped JSON report to `data/v9_product_behavior.json`. It is the shortest regression entry point for:

- rough request clarification quality
- backend degradation guidance
- terminal execution-aware output consistency
- terminal repair guidance for backend/runtime blocked states
- runtime recovery guidance for missing environment pieces and probe-harness failures
- explicit unsupported refusal behavior
- supported workflow generation states
- probe artifact consistency

The dedicated v11 task-suite validator writes `data/v11_task_suite.json`. It is the shortest regression entry point for:

- realistic natural-language task coverage
- candidate-target / formula / workflow preview behavior
- clarification-vs-unsupported routing
- nearest-grounded recovery expectations for supported-edge and unsupported-edge requests

V9 closeout gate classes:

- Grounded generation / handoff proved:
  `scripts/validate_supported_workflows.py`, `scripts/validate_v9_product_behavior.py`, `scripts/validate_v11_task_suite.py`, and `scripts/refresh_goal_audit.py` prove coherent grounded generation and HPC handoff readiness for the current `11` families / `17` targets.
- Backend usable:
  `scripts/validate_backend_execution.py` proves whether the real CLI path can currently use `auto`, `api`, or `codex`, or whether those paths remain explicit fallback-only routes.
- Local runtime proved:
  none of these default closeout commands prove local numerical execution unless a probe artifact actually reaches `runtime_proved`.
- Product-behavior gates:
  `scripts/validate_v9_product_behavior.py` plus the two minimal CLI product-path checks below prove clarification behavior, terminal execution-aware output, backend/runtime recovery guidance, and explicit unsupported refusal.
- Structure/coherence gates:
  `$PYTHON_BIN -B -m unittest`, `scripts/validate_backend_execution.py`, `scripts/validate_supported_workflows.py`, `scripts/validate_v11_task_suite.py`, and `scripts/refresh_goal_audit.py` prove contract stability, backend-path accounting, supported-workflow artifact coherence, realistic task-suite behavior, and audit aggregation.
- Not a local runtime-proof gate:
  none of those closeout commands prove that this workstation can numerically run PyQUDA end to end. They prove grounded generation and explicit runtime/probe reporting, not local `runtime_proved`.

What the closeout artifacts prove, and what they do not:

- `data/backend_execution.json`
  Proves the real CLI backend interpretation path, backend/fallback categories, and rough-request lifecycle coherence across `auto` / `api` / `codex`.
  It is the backend-usable report, not the grounded-generation proof and not the local-runtime proof.
  It does not prove supported-workflow script generation or local numerical execution.
- `data/supported_workflows_validation.json`
  Proves coherent routing for each supported workflow family from rough and direct requests into grounded artifacts, generated scripts, and probe-status reporting across the current `11` families / `17` grounded targets.
  It is intentionally limited to supported paths; unsupported nearest-grounded recovery actions are summarized in `data/v9_product_behavior.json`.
  A coherent direct run may still stay at `generated_runtime_blocked` because the runtime environment is missing dependencies or because the explicit generated-script probe exposed a concrete blocker before reaching `runtime_proved`.
  It does not prove that the current workstation reaches `runtime_proved`.
- `data/v9_product_behavior.json`
  Proves the product-facing regression surface: clarification routing, terminal rendering, actionable recovery guidance, explicit unsupported refusal, and probe-artifact consistency.
  It is the source of truth for unsupported-action contracts such as `retry_supported_workflow` versus `choose_supported_variant`.
  It does not replace the structure/coherence validators or prove local runtime success.
- `data/v11_task_suite.json`
  Proves the realistic natural-language task-suite contract, including ambiguous physics clarification, candidate previews, and nearest-grounded recovery expectations for supported-edge and unsupported-edge requests.
  It is a task-behavior audit, not a backend-usable proof and not a local-runtime proof.

Minimal copyable product-path checks:

```bash
PYTHONPATH=src $PYTHON_BIN -m pyquda_agent.cli run \
  "please compute the pion two-point correlator" \
  --backend codex \
  --no-interactive \
  --result-format summary \
  --output outputs/v9_rough_check.py \
  --pyquda-repo ~/PyQUDA
```

```bash
PYTHONPATH=src $PYTHON_BIN -m pyquda_agent.cli run \
  "please compute the pion two-point correlator from gauge ~/PyQUDA/tests/weak_field.lime lattice size 4 4 4 8 grid 1 1 1 1 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed source timeslice 0 outputs/v9_pion.npy outputs/v9_pion.py resource_path=.cache/quda cluster_launch=local" \
  --backend codex \
  --no-interactive \
  --result-format summary \
  --runtime-probe \
  --probe-timeout 5 \
  --output outputs/v9_pion.py \
  --pyquda-repo ~/PyQUDA
```

Optional local runtime-only checks:

```bash
$PYTHON_BIN scripts/check_pyquda_runtime.py --pyquda-repo ~/PyQUDA
$PYTHON_BIN scripts/refresh_runtime_check.py --pyquda-repo ~/PyQUDA
$PYTHON_BIN scripts/probe_generated_workflow.py --script outputs/run_pion_api.py --output outputs/run_pion_api.probe.json
$PYTHON_BIN scripts/scan_runtime_candidates.py --pyquda-repo ~/PyQUDA
```

If you want generation plus probe in one command, use:

```bash
PYTHONPATH=src $PYTHON_BIN -m pyquda_agent.cli run \
  "please compute the pion two-point correlator from gauge ~/PyQUDA/tests/weak_field.lime lattice size 4 4 4 8 grid 1 1 1 1 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed source timeslice 0 outputs/pion.npy outputs/run_pion.py resource_path=.cache/quda cluster_launch=local" \
  --backend codex \
  --no-interactive \
  --runtime-probe \
  --probe-timeout 5 \
  --output outputs/run_pion.py \
  --pyquda-repo ~/PyQUDA
```

This writes the normal artifact chain plus `outputs/run_pion.probe.json`.
The main product path is now this unified `run` command. `scripts/probe_generated_workflow.py` remains useful when you want to re-probe an already generated script later without regenerating artifacts.
The CLI result now also exposes a unified `workflow_outcome` record so the user does not need to manually combine top-level `status`, `execution_status`, nested `runtime_evidence`, and `probe_hint` just to see where the run stands.
The same result now also exposes `product_status`, a single normalized lifecycle label for the most common user-facing states, such as `needs_input`, `ready_to_generate`, `generated_probe_available`, `generated_runtime_blocked`, `runtime_proved`, or `unsupported`.
For clients that want an even more direct product-style answer, the same result now also exposes `delivery_status`, which splits the current run into:

- generation state
- execution/probe state
- current primary next step

This makes generation success versus runtime-proof success explicit without flattening away the detailed `workflow_outcome` record.
For callers that want the same split without traversing nested delivery fields, the summary also exposes:

- `generation_result`, a thin generation-only card
- `execution_result`, a thin execution/probe-only card

These two fields are intentionally redundant with `delivery_status`; they exist so thin clients and terminal renderers can show "did code generation succeed?" and "what happened with runtime proof?" without reconstructing those answers from the broader lifecycle model.
For callers that want one even shorter execution-aware answer, the same result now also exposes `execution_closure`, which keeps:

- the dominant execution-aware `state`
- one `headline`
- the current generation and execution phases
- the current backend/runtime blocker subtype
- the next artifact to inspect
- the next copyable command, when one is available

For callers that want an even more product-like checkpoint card, the same result now also exposes `execution_checkpoint`, which keeps:

- the current checkpoint `state`
- the current `runtime_level`
- the concrete probe status from the current run
- whether the generated script is already ready for HPC handoff even if runtime proof is still blocked
- the next artifact and next action to use

For callers that want one compact record for the whole product path, the same result now also exposes `workflow_lifecycle`, which keeps:

- the current lifecycle `stage`
- the current `blocking_kind`
- nested `generation` and `runtime` substates
- the current `next` action
- the most relevant emitted artifact paths

This gives frontends one stable object for `clarification -> generation -> probe/runtime` without losing the more detailed records.
For callers that want one probe-focused diagnosis without unpacking the whole probe payload, the same result now also exposes `runtime_diagnostic`, which distinguishes:

- `probe_available`
- `runtime_missing`
- `probe_driver_failed`
- `runtime_proved`

This keeps “fix the PyQUDA/runtime environment” separate from “fix the probe harness or local probe path”.
For backend-aware callers, the same result now also keeps short codex-preflight timeouts separate from the final backend outcome. In `auto` mode without a configured API backup, and in explicit `--backend codex` runs, a short codex preflight timeout now records:

- `llm_codex_preflight_status=failed`
- `llm_codex_preflight_soft_failed=true`
- `llm_codex_preflight_soft_failure_reason=...`

while still allowing the real codex invocation to run. If that later full invocation also fails, the result then records the final fallback under the normal `llm_fallback_*` and `backend_diagnostic` fields. This makes “short smoke test timed out” distinct from “the actual LLM-assisted interpretation call failed.”
When a run resumes from a saved session, `auto` backend selection may also reuse the last backend outcome to avoid repeating a recently degraded codex path before trying a configured API route. The result keeps this explicit through `session_backend_memory_considered`, `session_backend_memory_used`, and `session_backend_prior_category`.
For product-style consumers that want one even smaller capability card, the same result now also exposes `capability_summary`, which compresses the current state into:

- backend capability
- generation capability
- runtime-evidence capability
- the current primary next step

This view is additive: it reuses the same underlying `workflow_outcome`, `delivery_status`, and `backend_diagnostic` semantics instead of defining a second independent lifecycle model.
For backend-focused consumers that still want a thinner record than `backend_diagnostic`, the same result now also exposes `backend_path`, which keeps the requested backend, selected backend, failure category/origin, whether the current grounded result is still usable, and the current backend-repair action if one exists.
For HPC handoff, the same result now also exposes `hpc_handoff`, which mirrors the generated script's submission contract: concrete input paths, propagator/gauge input manifests, immutable-input policy for propagator-entry branches, output paths, rank-0 write policy, required runtime modules, probe artifact path, and the current preflight checks to review before cluster submission.
For plain terminal use, the same result now also exposes `terminal_message`, which distills the current outcome into:

- `headline`
- `detail`
- `recommended_command`
- `alternative_commands`

The CLI `--result-format terminal` path renders those fields as a small card:

- `Outcome: ...`
- `Detail: ...`
- `Reason: ...` when the run is blocked, degraded, or explicitly falling back
- `Status:` with compact `Backend`, `Generation`, and `Runtime` states
- `Execution: <state> | inspect=<artifact> | next=<action>` from `execution_closure`
- `Execution detail: ...` with the shortest execution-aware interpretation of the current state
- `Checkpoint: <state> | runtime=<level> | probe=<status>` from `execution_checkpoint`
- `Checkpoint detail: ...` with the shortest handoff/probe-oriented interpretation of the current state
- optional `Backend class: ...` or `Runtime class: ...` when that classification is actionable
- optional `Physics: ...` plus `Candidates: ...` when a rough request still needs target confirmation
- optional `Formula candidates: ...` lines when the request is genuinely ambiguous and the agent has multiple operator/formula candidates to show before asking for confirmation
- optional `Clarification: ...`, `Next prompt: ...`, and `Example answer: ...` for the current clarification batch
- optional `Workflow: ...`, `Runtime evidence: ...`, and `Actionability: ...` so a terminal user can immediately see the matched workflow family, current runtime/probe evidence level, and whether the primary next step is already copyable
- optional `Continuation: ...`, `Backend retry: ...`, and `Runtime retry: ...` so degraded or blocked runs show whether the current path can continue immediately and whether retrying the backend or probe is meaningful
- optional `Backend fix: ...`, `Backend fix detail: ...`, and `Backend fix command: ...` when backend assistance degraded but the run still has a grounded continuation path, so terminal users can see both "continue now" and "repair backend later" without opening JSON
- optional `Runtime fix: ...`, `Runtime fix detail: ...`, and `Runtime fix blocker: ...` when execution evidence is blocked after script generation, so terminal users can separate the repair prerequisite from the retry command
- `Results:` with the normalized generation result and execution result phases
- `Artifacts:` with the most relevant emitted paths, such as session / physics / task / plan / script / probe
- `Inspect first: ...` pointing to the first artifact a human usually wants to open
- `Command:`
- `Options:` for actionable alternatives, when present

This is meant to be read directly by humans or thin wrappers that do not want to fuse several lower-level fields before displaying a conclusion.
When a run ends in clarification or dry-run state, the underlying continuation hints still preserve `--result-format terminal`, so copied follow-up commands remain in the same display mode.
The same unified path now accepts `--llm-timeout` so backend-assisted interpretation can fail fast and fall back explicitly instead of appearing to hang indefinitely.
In `--backend auto`, the run path now records how codex was evaluated before selecting `codex`, `api`, or `rules`: most paths still use a short local codex preflight, while the rough normalization-only path without a configured API backup can skip preflight entirely and go straight to the real codex call. The summary surfaces that decision through `backend_selection_reason` plus `llm_codex_preflight_*` fields.
The intent-interpreter prompt sent to the backend is now compact as well: it includes candidate targets, the current inferred/confirmed target state, compact formula summaries, and counts for local references / curated citations, while leaving full curated citation payloads and full local-reference lists in the emitted artifacts instead of the LLM request.
For clearly identified rough requests, that first backend prompt also skips detailed formula/operator proposal payloads and keeps them for ambiguous interpretation cases only.
If the first backend-assisted intent call times out, the resolver now performs at most one explicit timeout-recovery retry with a smaller prompt and a shorter capped backend timeout before settling on final fallback. That retry is recorded separately from the original call through `llm_timeout_recovery_*` summary fields and the mirrored `llm_assistance` / `backend_diagnostic` records.
For local `codex`, the initial intent-interpretation call now also uses its own shorter cap before that recovery path starts, and the summary records it through `llm_intent_primary_timeout_seconds`. This keeps rough-request clarification from always waiting for the backend's full general timeout budget before recovery or fallback can begin.
That cap is now strategy-aware: the rough `normalization_only` codex path uses a shorter first-attempt cap than the heavier full-interpretation path.
When backend assistance fails or falls back, the summary now also exposes `backend_diagnostic`, which keeps the machine-readable failure category but adds a human-oriented `next_step` and `recommended_fix`.
That diagnostic now distinguishes additional real-world API failure classes too, including `endpoint_not_found`, `request_error`, `response_parse_error`, and `empty_response`, so “provider/base-url mismatch” does not collapse into the same recovery path as “retry later”.
The same summary now also exposes an ordered `action_queue`, which puts the most likely next command first and keeps optional backend/runtime repair guidance as secondary actions instead of forcing the user to compare `reply_hint`, `set_hint`, `probe_hint`, and diagnostics manually.
If a client only wants one next step, it can read `primary_action` directly instead of indexing the queue, and `actionable` tells it whether the suggested step is already a copyable command.
For terminal dashboards or thin UI clients, the same result now also exposes `run_overview`, a compact card that summarizes the current phase, headline, blocking kind, backend state, runtime level, and primary action without making the caller recompute status priority across several fields.
The same structured summary now also exposes:

- `schema_family` / `schema_version`, so product clients can pin to an explicit summary contract
- `blocking_reason`, a one-line explanation of the current blockage or degraded state
- `blocking_reason_detail`, a structured category/source record for that same blockage, with finer backend/runtime subtypes when available
- `inspection_hint`, a machine-readable pointer to the first artifact a human usually wants to inspect next
- `frontend_profile`, a compact frontend-oriented card payload that reuses the same status semantics but avoids forcing thin clients to stitch together `run_overview`, `capability_summary`, `primary_action`, and `inspection_hint` manually

The terminal renderer now reuses those summary fields directly instead of recomputing separate CLI-only heuristics.
The current product-facing state vocabulary is summarized separately in `docs/RESULT_SUMMARY_TAXONOMY.md`.
In the full JSON payload, these same stable product-facing fields are also mirrored at top level so callers do not have to descend into `result_summary` for common status-card use.
When a request is explicit but unsupported, the same summary also exposes:

- `supported_workflows`, the full current grounded workflow-family catalog
- `nearby_supported_workflows`, the nearest subset for the current target family
- `unsupported_guidance`, which highlights the primary conflict and the adjustment hints for those nearby families
- `unsupported_guidance.primary_scope`, which says whether the nearest grounded mismatch is on the `physics`, `implementation`, or `runtime` side
- `unsupported_guidance.shortest_fix.scope_breakdown`, which groups the minimum required changes by the same scopes

When a nearby family can be reached by one deterministic grounded correction, `unsupported_guidance.retry_suggestions` may also include a direct `retry_command`.
When the user still has to choose among grounded alternatives, the same structure can instead expose a small set of `variant_retry_commands`, for example a `wall` branch and a `point` branch for the propagator-entry pion family.

This keeps refusals honest while still telling the user which grounded paths are closest to the rejected request.

If you do not need to run the script locally, these runtime checks are not part of the default done condition. The repository can validate structure, traceability, and HPC handoff readiness without a local PyQUDA runtime.

`implementation_plan.runtime_readiness` now reports a stable evidence ladder:

- `syntax_valid`
- `structurally_grounded`
- `runtime_ready`
- `runtime_proved`
- `current_level`
- `blockers`

`blockers` now include actionable runtime suggestions, not only failing module names.
The same record now also carries `generated_script_probe` metadata so the run output tells you exactly which explicit probe command would move a result from `runtime_ready` toward `runtime_proved`, without auto-running a potentially expensive inversion job.
When `--runtime-probe` is requested, the probe result is persisted as a sibling `*.probe.json` artifact, reflected under top-level `execution_status`, and mirrored inside `runtime_evidence.generated_script_probe`.
`runtime_evidence.probe_policy` now also distinguishes the default opt-in policy from the current run's actual probe request/attempt status, so artifact reviewers can see whether probe execution merely remained available or was actually requested in this run.
If the probe harness itself fails before the generated script can be assessed, the main `run` result still keeps the emitted script and records `execution_status=probe_driver_failed` plus a structured `probe_driver_error` in the probe artifact instead of aborting the whole generation path.
The same distinction is now reflected in product-facing fields too: `delivery_status.execution`, `runtime_diagnostic`, `terminal_message`, and `run_overview.blocking_kind` no longer collapse probe-driver failures and environment-missing failures into one generic runtime state.
For runtime-side blocked states, `runtime_diagnostic` now also carries a more direct repair suggestion path: `recommended_fix` summarizes the most specific currently known repair action, while `retry_command` mirrors the probe command when a retry is meaningful. This is intentionally parallel to `backend_diagnostic`, so thin clients can render one repair card shape for both backend-side and runtime-side failures.
