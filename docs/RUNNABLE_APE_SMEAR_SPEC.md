# Runnable APE-Smear Spec

This document fixes the first supported `ape_smear` family to one narrow grounded path only:

- start from a gauge configuration
- read a Chroma/QIO gauge file
- copy the gauge field
- apply `apeSmearChroma(1, 2.5, 4)`
- write one `.npy` smeared-gauge artifact

## Required inputs

- `start_from=gauge`
- `gauge_format=chroma_qio`
- `gauge_path=/path/to/cfg.lime`
- `lattice_size`, for example `24 24 24 72`
- `grid_size`, for example `1 1 1 2`
- `correlator_output_format=npy`
- `correlator_output_path=outputs/ape_smeared_gauge.npy`
- `resource_path`, for example `.cache/quda`
- `cluster_launch`, for example `slurm`

## Fixed workflow contract

- `task_type = ape_smear`
- `workflow_id = ape_smear_chroma_qio_npy_v1`
- no propagator input
- no source/sink variants beyond the gauge-output contract
- no momentum projection
- no gauge fixing step
- fixed APE parameters:
  - `steps = 1`
  - `alpha = 2.5`
  - `dir_ignore = 4`

## Grounding

The implementation is pinned to:

- `~/PyQUDA/tests/test_smear.py`
- `~/PyQUDA/tests/test_io.py`
- `~/PyQUDA/pyquda_utils/io/__init__.py`

It is not a generic APE-smearing template. Requests for different APE parameters or different IO families must remain explicit. HYP smearing now has its own separate runnable `hyp_smear_chroma_qio_npy_v1` family rather than silently reusing this APE path.
