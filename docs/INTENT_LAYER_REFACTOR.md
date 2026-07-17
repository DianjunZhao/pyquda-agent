# Intent Layer Refactor

## Goal

The current architecture stops treating any single runnable workflow as the system-level parser. The pipeline is split into:

1. `intent / physics interpretation`
2. `PyQUDA implementation grounding`

Supported implementation targets are now:

- `pion_2pt_chroma_wall_local_zero_momentum_npy_v1`
- `pion_2pt_existing_propagator_local_zero_momentum_npy_v1`
- `pion_dispersion_chroma_point_momentum_npy_v1`
- `proton_2pt_chroma_wall_local_zero_momentum_npy_v1`
- `proton_2pt_existing_propagator_local_zero_momentum_npy_v1`
- `meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1`
- `quark_propagator_chroma_point_hdf5_v1`
- `quark_propagator_gaussian_shell_chroma_hdf5_v1`

They are all reached through explicit matching instead of being the default interpretation.

## Module Boundaries

### `pyquda_agent.intent`

- `interpreter.py`
  Parses rough natural language into candidate physics targets, inferred interpretations, formula/operator proposals, and confirmation status.
- `clarifier.py`
  Builds and applies physics-first clarification questions.
- `schema.py`
  Holds the machine-readable physics artifact and shared clarification-question schema.

### `pyquda_agent.workflows`

- `matcher.py`
  Maps a confirmed physics target onto one of the supported implementation targets and reports explicit unsupported reasons otherwise.

### Existing implementation layer

- `tasks/parser.py`
  Keeps parsing concrete implementation/runtime fields from user text, but no longer decides the workflow.
- `tasks/clarifier.py`
  Only asks implementation/runtime questions after the physics target is confirmed and matched.
- `generator/*`
  Builds the grounded implementation plan and emits the matching runnable complete script once workflow matching succeeds.

## State Flow

`user request`
-> `physics artifact (.physics.json)`
-> `clarification loop`
-> `workflow match`
-> `implementation task spec (.task.json)`
-> `reference-grounded plan (.plan.json)`
-> `final runnable script (.py)`

The physics artifact records inferred vs confirmed interpretations, formula proposals, citations, backend/fallback provenance, and unsupported reasons. The task artifact records clarified implementation/runtime fields plus fixed-by-workflow fields. Complete generation is blocked until:

- a key physics target is confirmed
- the matcher selects a supported workflow
- all remaining implementation/runtime fields are resolved
