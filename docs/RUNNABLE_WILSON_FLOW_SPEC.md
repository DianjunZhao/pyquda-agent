# Runnable Wilson Flow Spec

This repository supports one narrow `wilson_flow` family pinned to the local PyQUDA Wilson-flow test path. It is not a generic flow-observable framework.

## Fixed implementation target

- `task_type = wilson_flow`
- `workflow_id = wilson_flow_chroma_qio_energy_npy_v1`
- start from `gauge`
- gauge format `chroma_qio`
- output format `.npy`

## Required inputs

- `gauge_path`: Chroma/QIO gauge file such as `cfg_0001.lime`
- `lattice_size`: four integers
- `grid_size`: four integers
- `flow_steps`: positive integer
- `flow_epsilon`: positive float
- `correlator_output_path`: output `.npy` path for the Wilson-flow energy history
- `script_output_path`
- `resource_path`
- `cluster_launch`

## Grounded PyQUDA path

The complete script must stay close to these local references:

- `~/PyQUDA/tests/test_wflow.py`
- `~/PyQUDA/tests/test_io.py`
- `~/PyQUDA/pyquda_utils/io/__init__.py`

The grounded API path is:

1. `core.init(GRID_SIZE, LATTICE_SIZE, resource_path=...)`
2. `io.readQIOGauge(...)`
3. `gauge.copy()`
4. `gauge_wflow.wilsonFlowChroma(flow_steps, flow_epsilon)`
5. `np.save(...)`

## Out of scope for v1

- saving the flowed gauge as an additional artifact
- alternative gauge formats
- alternative flow observables
- HMC / scale-setting / generic gauge-evolution wrappers
