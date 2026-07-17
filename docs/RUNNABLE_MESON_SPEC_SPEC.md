# Runnable Meson Spec Spec

This document defines the supported **complete runnable** meson-spectroscopy workflows in the current `pyquda-agent` suite.

The scope is intentionally narrow:

- use a `wall` source
- use a `local` sink contraction
- use exactly two fixed gamma-insertion channels:
  - `gamma5_gamma5`
  - `gamma4gamma5_gamma4gamma5`
- use a non-empty momentum list drawn from the locally grounded `|p|^2 <= 9` family from `phase.getMomList(9)`
- output a source-timeslice-resolved meson correlator tensor to `.npy`

Supported branches:

1. gauge entry
- start from a `Chroma/QIO` gauge configuration
- use `Clover`
- perform the full source-timeslice sweep `t_src = 0..Lt-1`

2. propagator entry
- start from existing stored propagators in `npy`, `hdf5`, or `chroma_qio` format
- require the stored propagators to already follow the grounded wall-source mesonspec path
- require one explicit `source_timeslice` per propagator path

Primary local references:

- `~/PyQUDA/tests/test_mesonspec.py`
- `~/PyQUDA/tests/test_io.py`
- `~/PyQUDA/pyquda_utils/io/__init__.py`
- `~/PyQUDA/pyquda_utils/core.py`
- `~/PyQUDA/pyquda_utils/gamma.py`
- `~/PyQUDA/pyquda_utils/phase.py`

Required inputs before complete generation:

- lattice size and grid size
- output path, `resource_path`, and runtime/cluster assumption

Gauge-entry-only required inputs:

- gauge path and gauge format
- `mass`, `xi_0`, `nu`, `coeff_t`, `coeff_r`
- solver tolerance and max iterations

Propagator-entry-only required inputs:

- propagator format and one or more propagator paths
- one `source_timeslice` per propagator path

Workflow-fixed choices shared by both branches:

- `task_type = meson_spec`
- `source_type = wall`
- `sink_type = local`
- `gamma_insertions = [gamma5_gamma5, gamma4gamma5_gamma4gamma5]`
- `momentum_projection = explicit`
- momentum vectors must stay inside the locally grounded `|p|^2 <= 9` family; the full family remains the default when the user does not request a grounded subset
- `gauge_fixed = false`
- `correlator_output_format = npy`
- `script_style = complete`

Gauge-entry fixed choices:

- `workflow_id = meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1`
- `start_from = gauge`
- `has_existing_propagators = false`
- `gauge_format = chroma_qio`
- `fermion_action = clover`

Propagator-entry fixed choices:

- `workflow_id = meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1`
- `start_from = propagator`
- `has_existing_propagators = true`

Important runtime boundary:

- both branches are only grounded for `GRID_SIZE[3] == 1`
- the gauge-entry branch performs the full source-timeslice sweep `t_src = 0..Lt-1` in the same structural style as `test_mesonspec.py`
- the propagator-entry branch does not regenerate propagators; it only reuses grounded IO helpers plus the same mesonspec contraction pattern

This workflow family is for **one fixed meson-spectroscopy correlator family**, not a generic meson correlator generator. If the user asks for a different gamma-insertion set, a different momentum family, a different source construction, a different hadron channel, or an ungrounded stored-propagator convention, the system must refuse complete mode rather than emit pseudocode.
