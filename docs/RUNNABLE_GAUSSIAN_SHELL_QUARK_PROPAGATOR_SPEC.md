# Runnable Gaussian-Shell Quark Propagator Spec

This document fixes one additional `quark_propagator` branch to a narrow, reviewable path grounded in local PyQUDA references. It is not a generic shell-source generator.

## Fixed workflow

- start from a Chroma/QIO gauge configuration
- build a point-source propagator seed at spatial origin `[0, 0, 0]` and one explicit `source_timeslice`
- apply `source.gaussianSmear(point_source, gauge, rho=2.0, n_steps=5)`
- build a Clover solve through `pyquda_utils.core.getClover(...)`
- invert with `pyquda_utils.core.invertPropagator(...)`
- save one HDF5 propagator artifact

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
- `source_smearing_kind=gaussian_shell`
- `source_smearing_rho=2.0`
- `source_smearing_steps=5`
- `sink_type=propagator`
- `momentum_projection=none`
- `gauge_fixed=false`

Unsupported variations, such as alternate shell parameters, wall sources, correlator output, or propagator-entry shortcuts, must be rejected explicitly.

## Grounded PyQUDA references

- `~/PyQUDA/tests/test_gaussian.py`
- `~/PyQUDA/tests/test_io.py`
- `~/PyQUDA/pyquda_utils/source.py`
- `~/PyQUDA/pyquda_utils/core.py`
- `~/PyQUDA/pyquda_utils/io/__init__.py`

These references define the concrete Gaussian shell-source helper, inversion path, gauge IO path, and `saveH5(...)` output contract used by the generated script.
