# PyQUDA Architecture Summary

This document is generated from `data/pyquda_index.json` by `scripts/render_pyquda_architecture.py`.

## Repository shape

- Indexed scopes: `pyquda_core`, `pyquda_utils`, `pyquda_io`, `pyquda_plugins`, `tests`, `examples`.
- Indexed files: 134 total, with 101 Python files and 4 Cython sources.
- Top-level packaging files: `.gitattributes`, `.gitignore`, `.gitmodules`, `LICENSE`, `MANIFEST.in`, `README.md`, `pyproject.toml`, `setup.py`.

## Layered architecture

- `pyquda_core` owns the `pyquda` runtime package and `pyquda_comm`, which initialize MPI/device state and expose QUDA-backed field, Dirac, action, and HMC APIs.
- `pyquda_utils` is a pure-Python layer that imports `pyquda` and `pyquda_comm` to provide source construction, phases, FFT, eigensolvers, HMC parameters, and convenience wrappers.
- `pyquda_io` is a format-oriented layer that re-exports readers and writers for Chroma, MILC, KYU, XQCD, NERSC, OpenQCD, NPY, and LIME-based workflows.
- `pyquda_plugins` builds optional compiled extensions against external libraries and ships plugin-facing packages such as `pycontract` and `pygwu`.
- `tests` and `examples` sit on top of those layers and act as the main executable surface for users and regression coverage.

## Notable entry points

- `pyquda` entry point: `pyquda_core/pyquda/__init__.py` exports initialization helpers and is the runtime front door for QUDA setup.
- `pyquda_io` entry point: `pyquda_io/__init__.py` re-exports file-format readers and writers from format-specific modules.
- `pyquda_plugins` CLI: `pyquda_plugins/__main__.py` builds and installs plugin extensions by driving Cython and setuptools.

## Core bindings and runtime

- Scope: `pyquda_core` with 39 indexed files.
- File mix: `cython`=4, `other`=8, `package-init`=4, `python`=23.
- Representative modules: `pyquda`, `pyquda.__main__`, `pyquda._version`, `pyquda.action`, `pyquda.action.abstract`.

## High-level utilities

- Scope: `pyquda_utils` with 20 indexed files.
- File mix: `package-init`=2, `python`=18.
- Representative modules: `pyquda_utils`, `pyquda_utils.alg_remez`, `pyquda_utils.checksum`, `pyquda_utils.convert`, `pyquda_utils.core`.
- Internal dependencies observed from Python imports: `pyquda_core` (36).

## Format I/O layer

- Scope: `pyquda_io` with 13 indexed files.
- File mix: `package-init`=1, `python`=12.
- Representative modules: `pyquda_io`, `pyquda_io.chroma`, `pyquda_io.ildg`, `pyquda_io.io_general`, `pyquda_io.io_utils`.
- Internal dependencies observed from Python imports: `pyquda_core` (1).

## Plugin builder

- Scope: `pyquda_plugins` with 4 indexed files.
- File mix: `package-init`=2, `python`=2.
- Representative modules: `pyquda_plugins.__main__`, `pyquda_plugins.plugin_pyx`, `pyquda_plugins.pycontract`, `pyquda_plugins.pygwu`.
- Internal dependencies observed from Python imports: `pyquda_core` (4), `pyquda_utils` (1).

## Validation surface

- Scope: `tests` with 49 indexed files.
- File mix: `test`=49.
- Representative modules: `check_pyquda`, `generate_resource`, `test_checksum`, `test_clover`, `test_clover_cli`.
- Internal dependencies observed from Python imports: `pyquda_core` (15), `pyquda_io` (1), `pyquda_plugins` (1), `pyquda_utils` (34).

## Example workflows

- Scope: `examples` with 9 indexed files.
- File mix: `example`=9.
- Internal dependencies observed from Python imports: `pyquda_core` (6), `pyquda_utils` (6).

## Analysis notes

- Vendored or embedded directories such as `pycparser` and `quda` are excluded from the generated index to keep dependency signals focused on project-owned code.
- The root `pyproject.toml` packages `pyquda_utils`, `pyquda_io`, and `pyquda_plugins`, while `pyquda_core/pyproject.toml` separately packages the `pyquda` runtime and `pyquda_comm` bindings.
- There is no in-repo `docs/` directory upstream; examples and tests currently serve as the clearest executable documentation surface.
