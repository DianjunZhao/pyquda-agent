# Runnable Pion 2pt Spec

This document defines the first supported **complete runnable** pion two-point workflow for `pyquda-agent`.

The main path is fixed:

`natural language request -> structured task spec -> clarification loop -> reference-grounded implementation plan -> complete script -> minimal validation`

`complete script` is not the primary artifact. The structured task spec and grounded plan must exist first and remain reviewable.

## Fixed scope for v1

The first version supports exactly one narrow path:

- start from a **Chroma/QIO gauge configuration**
- use **Clover** action parameters supplied by the user
- build a **wall source**
- use a **local sink**
- compute a **single pion two-point correlator**
- use **zero momentum**
- specify one or more **source timeslices**
- write correlator output to a **single `.npy` file**
- use the concrete local API path exercised by:
  - `~/PyQUDA/tests/test_mesonspec.py`
  - `~/PyQUDA/examples/3_Pion_Proton_2pt.py`
  - `~/PyQUDA/tests/test_io.py`
  - `~/PyQUDA/pyquda_utils/io/__init__.py`

It does **not** claim support yet for:

- starting from existing propagators
- nonzero momentum
- smeared sinks
- multiple task families
- guessed solver or lattice parameters
- placeholder complete scripts
- one-shot support for all pion 2pt variants

## Required inputs

### Physics choices

- `fermion_action = clover`
- `source_type = wall`
- `sink_type = local`
- `momentum_projection = zero`
- `momenta = [[0, 0, 0]]`
- `source_timeslices`
- `gauge_fixed`
- Clover parameter set:
  - `mass`
  - `xi_0`
  - `nu`
  - `coeff_t`
  - `coeff_r`

### PyQUDA implementation choices

- `start_from = gauge`
- `gauge_format = chroma_qio`
- `gauge_path`
- `lattice_size`
- `grid_size`
- `resource_path`
- `solver_tol`
- `solver_maxiter`

### Runtime and output choices

- `script_output_path`
- `correlator_output_format = npy`
- `correlator_output_path`
- `cluster_launch`

## Required intermediate artifacts

For a target script such as `outputs/run_pion.py`, the workflow must also emit:

- `outputs/run_pion.task.json`
- `outputs/run_pion.plan.json`

These are mandatory review artifacts for reproducibility and audit, not optional debug files.

## Real PyQUDA references used

- `~/PyQUDA/examples/3_Pion_Proton_2pt.py`
- `~/PyQUDA/examples/5_Pion_Dispersion.py`
- `~/PyQUDA/tests/test_mesonspec.py`
- `~/PyQUDA/tests/test_io.py`
- `~/PyQUDA/pyquda_utils/io/__init__.py`
- `~/PyQUDA/pyquda_utils/source.py`
- `~/PyQUDA/pyquda_utils/gamma.py`

## External physics citations recorded for v1

When the local PyQUDA code is not sufficient to justify the physics-side convention, the implementation plan also records curated citations under `implementation_plan.external_citations`.

The implementation plan also records `implementation_plan.convention_decisions`, which tie concrete workflow decisions to local PyQUDA references and, when needed, external citations.

When clarification answers are actually collected, the implementation plan records them under `implementation_plan.clarification_trace`.

The implementation plan may also record `implementation_plan.runtime_readiness`, which is optional local-environment evidence rather than a blocker on complete generation.

Current v1 citations are stored in:

- `data/physics_citations/pion_2pt_chroma_wall_local_zero_momentum_npy_v1.json`

They are refreshed from the source manifest:

- `data/physics_citations/pion_2pt_chroma_wall_local_zero_momentum_npy_v1.sources.json`
- `python3 scripts/refresh_physics_citations.py`

Optional metadata enrichment:

- `python3 scripts/refresh_physics_citations.py --enrich-from-arxiv`

Rendered citation entries record `metadata_source` and `metadata_refresh` so the plan artifact can distinguish curated fallback metadata from arXiv API metadata, and can also show when an attempted online refresh fell back to curated metadata.

They justify the chosen narrow convention:

- pion two-point correlator in the Euclidean lattice-spectroscopy setting
- local pseudoscalar pion operator
- zero-momentum projection
- wall source interpreted as selecting the `p=0` mode

## Real API path expected in complete mode

The complete script should be traceable to these concrete APIs and patterns:

- `from pyquda_utils import core, io, gamma`
- `core.init(grid_size, lattice_size, resource_path=...)`
- `latt_info = core.LatticeInfo(lattice_size, -1, xi_0 / nu)`
- `dirac = core.getClover(...)`
- `gauge = io.readQIOGauge(gauge_path)`
- `with dirac.useGauge(gauge):`
- `propagator = core.invert(dirac, "wall", t_src)`
- contraction via `cupy.einsum` using `gamma.gamma(15)` in the same shape pattern as `test_mesonspec.py`
- `core.gatherLattice(...)`
- `numpy.save(correlator_output_path, data)`
- the structured siblings `run_pion.task.json` and `run_pion.plan.json` must exist before the script is treated as reviewable complete output

## HPC handoff prerequisites

- A target HPC environment with PyQUDA, QUDA, GPU support, and the expected MPI/grid layout.
- `pyquda_utils`, `cupy`, and their runtime dependencies import successfully.
- The requested gauge path exists and is readable at runtime.
- The requested `grid_size` and `lattice_size` are consistent with the deployment.
- For a local source checkout, the upstream PyQUDA development steps must already be completed, including built core bindings and a Python import path that exposes both `pyquda` and `pyquda_utils`.

These are target-environment assumptions. The local workstation used to generate the script does not need to satisfy them in order for the script to be considered complete.

## Required handoff information inside the generated script

The complete script should also embed explicit handoff metadata and preflight checks:

- launch-mode assumption such as `local`, `mpi`, or `slurm`
- input visibility assumption: the gauge path must be readable from all ranks
- output ownership assumption: only rank 0 writes the final correlator file
- sibling artifact expectation: `*.task.json` and `*.plan.json` must exist next to the script
- lattice/grid divisibility checks before runtime initialization
- source-timeslice bounds checks before inversion
- output suffix and gauge suffix checks before runtime initialization

## Complete-mode acceptance criteria

A script may be labeled `complete` only if:

- all required fields are resolved
- the workflow matches the fixed v1 scope exactly
- imports are real PyQUDA imports
- contraction/inversion APIs are real and traceable to local references
- the script checks that the gauge file exists before attempting the run
- no `TODO`, `pass`, `placeholder`, or fake helper names remain
- the script passes Python syntax validation
- the script records enough cluster/runtime assumptions for handoff to an HPC environment

If any required field is missing or the request leaves the supported scope, the agent must continue clarification or refuse complete generation.
