# Task Schemas

## `pion_2pt`

Current v1 supports one fixed runnable workflow:

- `pion_2pt_chroma_wall_local_zero_momentum_npy_v1`

The supported flow is:

`natural language request -> structured task spec -> clarification loop -> reference-grounded implementation plan -> complete script -> minimal validation`

The first version is intentionally narrow so complete mode does not collapse into pseudocode.

### Draft fields

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
- `source_type`
- `sink_type`
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

### Resolution model

- The parser first produces a structured task draft.
- The clarifier asks for missing required fields instead of guessing.
- The implementation plan records:
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

The clarifier asks for fields in this order when missing:

1. start mode and whether existing propagators are involved
2. gauge or propagator format/path details
3. lattice size and grid size
4. Clover and solver parameters
5. source, sink, momentum, and source timeslice
6. gauge fixing
7. output path, resource path, cluster/runtime assumption, and script path
8. `script_style=complete`

### Intermediate artifacts

For an output script such as `outputs/run_pion.py`, the CLI also writes:

- `outputs/run_pion.task.json`
- `outputs/run_pion.plan.json`

`outputs/run_pion.task.json` captures the parsed and clarified task fields.

`outputs/run_pion.plan.json` captures references, convention decisions, runtime readiness, and the validation contract for complete generation.
