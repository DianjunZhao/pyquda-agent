# Runnable Pion Dispersion Spec

This document defines one supported **complete runnable** workflow in the current `pyquda-agent` suite.

The scope is intentionally narrow:

- start from a `Chroma/QIO` gauge configuration
- use `Clover`
- use a `point` source fixed at spatial origin `[0, 0, 0]`
- use a user-specified `source timeslice`
- use a non-empty momentum list drawn from the locally grounded 9-momentum family in `examples/5_Pion_Dispersion.py`
- output a momentum-indexed pion correlator array to `.npy`

Primary local references:

- `~/PyQUDA/examples/5_Pion_Dispersion.py`
- `~/PyQUDA/tests/test_mesonspec.py`
- `~/PyQUDA/tests/test_io.py`
- `~/PyQUDA/pyquda_utils/io/__init__.py`
- `~/PyQUDA/pyquda_utils/source.py`
- `~/PyQUDA/pyquda_utils/core.py`
- `~/PyQUDA/pyquda_utils/gamma.py`

Required inputs before complete generation:

- gauge path and gauge format
- lattice size and grid size
- `mass`, `xi_0`, `nu`, `coeff_t`, `coeff_r`
- solver tolerance and max iterations
- source timeslice list
- output path, `resource_path`, and runtime/cluster assumption

Workflow-fixed choices:

- `task_type = pion_dispersion`
- `workflow_id = pion_dispersion_chroma_point_momentum_npy_v1`
- `start_from = gauge`
- `source_type = point`
- `sink_type = local`
- `momentum_projection = explicit`
- momentum vectors must come from the local 9-momentum family; the full list remains the default when the user does not request a grounded subset
- `correlator_output_format = npy`
- `script_style = complete`

This workflow is for **pion dispersion-style momentum projection**, not a generic nonzero-momentum correlator generator. The agent may accept a reviewable subset of the validated local momentum family, but if the user asks for a different momentum family, a different source construction, or another hadron channel, the system must refuse complete mode rather than emit pseudocode.
