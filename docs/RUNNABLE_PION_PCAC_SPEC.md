# Runnable Pion PCAC Workflow

This repository supports one narrow runnable `pion_pcac` family grounded in `~/PyQUDA/examples/4_Pion_PCAC.py`.

## Fixed Scope

- `task_type = pion_pcac`
- `workflow_id = pion_pcac_chroma_wall_local_zero_momentum_npy_v1`
- `workflow_id = pion_pcac_existing_propagator_local_zero_momentum_npy_v1`
- start from either:
  - a Chroma/QIO gauge configuration
  - or existing wall-source propagators in `npy`, `hdf5`, or `chroma_qio` format
- use `getDirac` with the local multigrid block pattern
- apply one stout-smear step
- keep `wall` source, `local` sink, zero momentum
- contract both pion and pionA4 channels, then form the PCAC ratio
- write one `.npy` artifact ordered as `[pion, pionA4, ratio]`

## Required Inputs

- gauge-entry path:
  `gauge_path`, for example `~/PyQUDA/tests/weak_field.lime`
- propagator-entry path:
  `propagator_format`, `propagator_paths`, and one `source_timeslice` per propagator path
- `lattice_size`, for example `24 24 24 72`
- `grid_size`, for example `1 1 1 2`
- `source_timeslices`, for example `0`
- solver parameters: `mass`, `xi_0`, `nu`, `coeff_t`, `coeff_r`, `tol`, `maxiter`
  note: solver parameters are required only for the gauge-entry branch
- runtime paths: `resource_path`, correlator output path, script output path

## Fixed PyQUDA API Path

- gauge-entry:
  `io.readChromaQIOGauge(...)`
  `gauge.stoutSmear(1, 0.125, 4)`
  `core.getDirac(...)`
  `core.invert(dirac, "wall", t_src)`
- propagator-entry:
  `io.readNPYPropagator(...)` or `io.readQIOPropagator(...)` or `core.LatticePropagator.loadH5(...)`
- `gamma.gamma(8)` and `gamma.gamma(15)`
- `core.gatherLattice(...)`

## Runtime Assumptions

- `~/PyQUDA` remains read-only
- the gauge file is visible to all ranks
- only rank 0 writes the final `.npy`
- the target environment already provides `numpy`, `cupy`, `opt_einsum`, `pyquda_utils`, and `pyquda`

## Artifact Contract

- final `.npy` shape: `3 x Lt`
- channel order:
  `0 = pion`
  `1 = pionA4`
  `2 = pionA4 / pion`
- sibling review artifacts:
  `.physics.json`
  `.task.json`
  `.plan.json`
  `.probe.json`
