# Runnable Quark Propagator Spec

This document fixes the first `quark_propagator` branch to one narrow, reviewable path grounded in local PyQUDA references. It is not a generic propagator generator. For the separate Gaussian shell-source branch, see `docs/RUNNABLE_GAUSSIAN_SHELL_QUARK_PROPAGATOR_SPEC.md`.

## Fixed v1 workflow

- start from a Chroma/QIO gauge configuration
- build a Clover solve through `pyquda_utils.core.getDirac(...)`
- apply one stout-smear step: `steps=1`, `rho=0.125`, `ndim=4`
- use fixed multigrid blocks `[[6, 6, 6, 4], [4, 4, 4, 9]]`
- build a point source at spatial origin `[0, 0, 0]` with one explicit `source_timeslice`
- invert all spin-color components and save one HDF5 propagator artifact

## Required inputs

- `gauge_path`: Chroma/QIO gauge file visible on the target filesystem
- `lattice_size`: four integers
- `grid_size`: four integers compatible with the lattice extents
- Clover parameters: `mass`, `xi_0`, `nu`, `coeff_t`, `coeff_r`, `solver_tol`, `solver_maxiter`
- `source_timeslice`: exactly one timeslice
- output path ending in `.h5` or `.hdf5`
- runtime assumptions such as `resource_path` and `cluster_launch`

## Fixed implementation choices

- `start_from=gauge`
- `gauge_format=chroma_qio`
- `source_type=point`
- `sink_type=propagator`
- `momentum_projection=none`
- `gauge_fixed=false`

Unsupported variations, such as wall sources, correlator output, alternate smear settings, or ungrounded propagator formats, must be rejected explicitly.

## Grounded PyQUDA references

- `~/PyQUDA/examples/2_Quark_Propagator.py`
- `~/PyQUDA/tests/test_io.py`
- `~/PyQUDA/pyquda_utils/source.py`
- `~/PyQUDA/pyquda_utils/core.py`
- `~/PyQUDA/pyquda_utils/io/__init__.py`

These references define the concrete source construction, inversion path, gauge IO path, and `saveH5(...)` output contract used by the generated script.

## HPC handoff expectations

- the script assumes PyQUDA, QUDA, CuPy, NumPy, and HDF5 support are already available
- the gauge input and output directory must be visible to all ranks
- sibling `.physics.json`, `.task.json`, and `.plan.json` artifacts should be reviewed before submission
- failure checks should stop early on missing gauge files, invalid grid divisibility, or mismatched output suffixes
