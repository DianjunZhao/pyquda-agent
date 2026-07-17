# Runnable Proton 2pt Spec

This workflow family is intentionally narrow. Complete mode now supports two grounded proton paths:

1. gauge entry
- start from a `chroma_qio` gauge configuration
- apply one fixed stout-smearing step
- build the operator with `pyquda_utils.core.getDirac(...)`
- use a `wall` source at user-specified `source_timeslice`
- use the parity-projected zero-momentum proton contraction from `examples/3_Pion_Proton_2pt.py`
- write the correlator to `.npy`

2. propagator entry
- start from existing stored propagators in `npy`, `hdf5`, or `chroma_qio` format
- require `wall` source convention and explicit `source_timeslice` for each propagator path
- reuse the same parity-projected zero-momentum proton contraction from `examples/3_Pion_Proton_2pt.py`
- do not regenerate propagators, rebuild the Dirac operator, or apply gauge smearing inside this branch
- write the correlator to `.npy`

## Required inputs

Gauge-entry branch:

- `gauge_path`
- `lattice_size`
- `grid_size`
- `mass`
- `xi_0`
- `nu`
- `coeff_t`
- `coeff_r`
- `solver_tol`
- `solver_maxiter`
- `source_timeslices`
- `resource_path`
- `cluster_launch`
- `correlator_output_path`
- `script_output_path`

Propagator-entry branch:

- `propagator_format`
- `propagator_paths`
- `lattice_size`
- `grid_size`
- `source_timeslices`
- `gauge_fixed`
- `resource_path`
- `cluster_launch`
- `correlator_output_path`
- `script_output_path`

## Fixed-by-workflow choices

- `task_type = proton_2pt`
- `workflow_id = proton_2pt_chroma_wall_local_zero_momentum_npy_v1`
- `start_from = gauge`
- `fermion_action = clover`
- `source_type = wall`
- `sink_type = local`
- `momentum_projection = zero`
- `momenta = [[0, 0, 0]]`
- `gauge_fixed = false`
- `multigrid_blocks = [[6, 6, 6, 4], [4, 4, 4, 9]]`
- `stout_smear_steps = 1`
- `stout_smear_rho = 0.125`
- `stout_smear_ndim = 4`

Propagator-entry branch:

- `workflow_id = proton_2pt_existing_propagator_local_zero_momentum_npy_v1`
- `start_from = propagator`
- `has_existing_propagators = true`
- `source_type = wall`
- `sink_type = local`
- `momentum_projection = zero`
- `momenta = [[0, 0, 0]]`
- `gauge_fixed = false`
- `correlator_output_format = npy`

## Grounding

Primary local references:

- `~/PyQUDA/examples/3_Pion_Proton_2pt.py`
- `~/PyQUDA/tests/test_io.py`
- `~/PyQUDA/pyquda_utils/io/__init__.py`
- `~/PyQUDA/pyquda_utils/source.py`
- `~/PyQUDA/pyquda_utils/core.py`
- `~/PyQUDA/pyquda_utils/gamma.py`

The generated script must stay close to these paths: real `pyquda_utils` imports, real `core.invert(...)`, real gauge IO, real color-permutation proton contraction, no TODOs, and no invented baryon helper APIs.

For the propagator-entry branch, the generated script must instead stay close to the local propagator IO helpers plus the same real proton contraction path. It must not invent a new baryon-storage format or a fake helper that bypasses the example/test grounding.
