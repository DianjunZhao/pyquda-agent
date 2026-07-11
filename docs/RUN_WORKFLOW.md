# Run Workflow

`pyquda-agent` keeps `~/PyQUDA` read-only and writes all derived artifacts inside this repository or to an explicit user output path.

## Primary path

The main path is:

`natural language request -> structured task spec -> clarification loop -> reference-grounded implementation plan -> complete script -> minimal validation`

For `pion_2pt` v1, this is intentionally narrow. It does not try to cover all pion correlator variants in one step, because that would degrade complete mode into guessed code.

## Refresh analysis artifacts

```bash
python3 scripts/refresh_pyquda_analysis.py
```

This updates:

- `data/pyquda_index.json`
- `docs/PYQUDA_ARCHITECTURE.md`

## First supported complete workflow

Current fixed workflow:

- start from `gauge`
- `chroma_qio` gauge input
- `clover`
- `wall` source
- `local` sink
- zero momentum only
- `.npy` correlator output only

Example end-to-end command:

```bash
PYTHONPATH=src python3 -m pyquda_agent.cli run \
  "generate complete runnable pion 2pt from gauge ~/PyQUDA/tests/weak_field.lime with clover wall source local sink zero momentum timeslice 0 lattice size 4 4 4 8 grid 1 1 1 1 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed outputs/pion.npy outputs/run_pion.py resource_path=.cache/quda" \
  --backend codex \
  --no-interactive \
  --output outputs/run_pion.py \
  --pyquda-repo ~/PyQUDA
```

Single-command refresh for the fixed demo artifacts:

```bash
python3 scripts/refresh_first_workflow_demo.py --pyquda-repo ~/PyQUDA --backend api
```

Direct backend parity check:

```bash
python3 scripts/check_backend_parity.py --pyquda-repo ~/PyQUDA
```

Local interpreter scan for an already-usable PyQUDA runtime:

```bash
python3 scripts/scan_runtime_candidates.py --pyquda-repo ~/PyQUDA
```

If the scan still reports no ready interpreter, use
[PYQUDA_RUNTIME_BOOTSTRAP.md](/Users/zhaodianjun/pyquda-agent/docs/PYQUDA_RUNTIME_BOOTSTRAP.md)
to align the Python environment with the upstream PyQUDA install/development paths already present on this machine.

Useful flags:

- `--dry-run`: stop after task spec, retrieval, and implementation plan
- `--no-interactive`: do not ask follow-up questions; return missing fields instead
- `--print-context`: print the retrieval bundle used for generation
- `--save-session state.json`: persist the structured task draft
- `--resume-session state.json`: continue from a saved draft

Generated intermediate artifacts:

- `outputs/run_pion.task.json`
- `outputs/run_pion.plan.json`
- `outputs/run_pion.py`

The script is the last artifact in the chain, not the first one to review. If required fields are missing, complete mode must stop at `needs_input` or `unsupported` instead of emitting template-style code.

Review order should follow the same pipeline:

1. inspect `*.task.json`
2. inspect `*.plan.json`
3. inspect the generated script

## Minimal validation

Recommended local checks:

```bash
python3 -B -m unittest tests.test_index_pyquda_repo tests.test_cli_run tests.test_task_parser tests.test_clarifier tests.test_context_builder tests.test_generator
python3 scripts/refresh_pyquda_analysis.py
python3 scripts/refresh_physics_citations.py
python3 scripts/refresh_physics_citations.py --enrich-from-arxiv
python3 scripts/check_pyquda_runtime.py --pyquda-repo ~/PyQUDA
python3 scripts/refresh_runtime_check.py --pyquda-repo ~/PyQUDA
python3 scripts/probe_generated_workflow.py --script outputs/run_pion_api.py --output data/run_pion_api_probe.json
python3 scripts/refresh_goal_audit.py
```

If you want to actually run a generated script, you also need a real PyQUDA runtime environment. The current repository can validate structure and reference-grounding without that environment, but numerical execution still depends on the upstream PyQUDA installation/build state.
