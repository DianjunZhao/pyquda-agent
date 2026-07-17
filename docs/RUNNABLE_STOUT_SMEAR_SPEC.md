# Runnable Stout-Smear Spec

This document fixes the first supported `stout_smear` family to one narrow grounded path only:

- start from a gauge configuration
- read a Chroma/QIO gauge file
- copy the gauge field
- apply `stoutSmear(1, 0.241, 3)`
- write one `.npy` smeared-gauge artifact

The same local `~/PyQUDA/tests/test_smear.py` evidence also demonstrates APE and HYP smear calls. This repository now ships separate runnable `ape_smear_chroma_qio_npy_v1` and `hyp_smear_chroma_qio_npy_v1` families instead of collapsing those requests into the stout path.

## Required inputs

- `gauge_format=chroma_qio`
- `gauge_path=/path/to/cfg.lime`
- `lattice_size`, for example `4 4 4 8`
- `grid_size`, for example `1 1 1 1`
- `resource_path`, for example `.cache/quda`
- `cluster_launch`, for example `slurm` or `local`
- `correlator_output_path`, which in this family is the smeared-gauge output path, for example `outputs/stout_smeared_gauge.npy`

## Fixed workflow choices

- `task_type=stout_smear`
- `start_from=gauge`
- `has_existing_propagators=false`
- `source_type=none`
- `sink_type=gauge`
- `momentum_projection=none`
- `gauge_fixed=false`
- `correlator_output_format=npy`
- `stout_smear_steps=1`
- `stout_smear_rho=0.241`
- `stout_smear_ndim=3`

Any other smear parameters or propagator-entry variants are currently out of scope and must be refused explicitly.

## Grounded PyQUDA path

The complete script must stay traceable to local `~/PyQUDA` references:

- `~/PyQUDA/tests/test_smear.py`
- `~/PyQUDA/pyquda_utils/io/__init__.py`

The real API path is:

```python
gauge = io.readQIOGauge(...)
gauge_stout = gauge.copy()
gauge_stout.stoutSmear(1, 0.241, 3)
io.writeNPYGauge(..., gauge_stout)
```

## Runtime and handoff assumptions

- PyQUDA and `pyquda_utils` must already be installed in the target Python environment.
- The gauge input path must be visible on the cluster filesystem.
- The script writes the final `.npy` output on rank 0 only.
- The sibling `.physics.json`, `.task.json`, and `.plan.json` artifacts are part of the handoff contract and must be reviewed before submission.
