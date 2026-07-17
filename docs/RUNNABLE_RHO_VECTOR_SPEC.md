# Runnable Rho Vector Spec

This rho/vector workflow family is intentionally narrow. It supports exactly two grounded paths:

- start from a Chroma/QIO gauge configuration
- build a Clover Dirac operator
- use a wall source at one or more explicit source timeslices
- use a local sink
- contract the spatial vector bilinear family
  `gamma1_gamma1`, `gamma2_gamma2`, `gamma3_gamma3`
- project to zero momentum only
- save a NumPy tensor ordered as `[source_timeslice, t, gamma_i]`
- or start from existing wall-source propagators in `npy`, `hdf5`, or `chroma_qio` format
- reuse the same spatial vector bilinear contraction without regenerating inversions

Required user inputs:

- `gauge_path` for the gauge-entry branch
- `propagator_format`, `propagator_paths`, and `source_timeslices` for the propagator-entry branch
- `lattice_size`
- `grid_size`
- `mass`, `xi_0`, `nu`, `coeff_t`, `coeff_r` for the gauge-entry branch
- `solver_tol`, `solver_maxiter` for the gauge-entry branch
- output `.npy` path and final script path

Fixed workflow constraints:

- gauge-entry branch:
  `start_from=gauge`, `gauge_format=chroma_qio`, `fermion_action=clover`
- propagator-entry branch:
  `start_from=propagator`, `propagator_format in {npy,hdf5,chroma_qio}`
- `source_type=wall`
- `sink_type=local`
- `momentum_projection=zero`
- `momenta=[[0,0,0]]`
- `gauge_fixed=false`
- `script_style=complete`

Grounding and provenance:

- physics-side operator choice uses model inference for the standard rho/vector channel `O_{rho,i} = \bar q \gamma_i q`
- implementation is grounded in local PyQUDA references:
  `tests/test_mesonspec.py`, `tests/test_mesonspec.ini.xml`, `tests/test_io.py`, `pyquda_utils/io/__init__.py`, `pyquda_utils/core.py`, `pyquda_utils/gamma.py`
- the propagator-entry branch is grounded by combining the same `test_mesonspec.py` contraction layout with the concrete propagator save/load paths exercised in `tests/test_io.py`

Runtime assumptions:

- PyQUDA, QUDA, CuPy, and NumPy are already installed on the target cluster environment
- the gauge file is visible to all ranks
- only rank 0 writes the final output
