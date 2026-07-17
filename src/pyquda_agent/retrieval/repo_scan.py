"""Read candidate files from the workspace and the read-only PyQUDA checkout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


WORKFLOW_FILES = (
    "docs/RUNNABLE_PION_2PT_SPEC.md",
    "docs/RUNNABLE_PION_PCAC_SPEC.md",
    "docs/RUNNABLE_PION_DISPERSION_SPEC.md",
    "docs/RUNNABLE_MESON_SPEC_SPEC.md",
    "docs/RUNNABLE_RHO_VECTOR_SPEC.md",
    "docs/RUNNABLE_PROTON_2PT_SPEC.md",
    "docs/RUNNABLE_QUARK_PROPAGATOR_SPEC.md",
    "docs/RUNNABLE_GAUSSIAN_SHELL_QUARK_PROPAGATOR_SPEC.md",
    "docs/RUNNABLE_APE_SMEAR_SPEC.md",
    "docs/RUNNABLE_HYP_SMEAR_SPEC.md",
    "docs/RUNNABLE_WILSON_FLOW_SPEC.md",
    "docs/RUNNABLE_STOUT_SMEAR_SPEC.md",
    "docs/TASK_SCHEMAS.md",
    "docs/RUN_WORKFLOW.md",
)

PION_2PT_PYQUDA_FILES = (
    "examples/3_Pion_Proton_2pt.py",
    "examples/5_Pion_Dispersion.py",
    "tests/test_mesonspec.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/source.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
)

PINNED_PION_2PT_PYQUDA_FILES = PION_2PT_PYQUDA_FILES
PINNED_PION_2PT_PROPAGATOR_PYQUDA_FILES = (
    "tests/test_mesonspec.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
    "examples/3_Pion_Proton_2pt.py",
)
PION_DISPERSION_PYQUDA_FILES = (
    "examples/5_Pion_Dispersion.py",
    "tests/test_mesonspec.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/source.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
    "examples/3_Pion_Proton_2pt.py",
)

PINNED_PION_DISPERSION_PYQUDA_FILES = PION_DISPERSION_PYQUDA_FILES
PION_PCAC_PYQUDA_FILES = (
    "examples/4_Pion_PCAC.py",
    "examples/3_Pion_Proton_2pt.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
)

PINNED_PION_PCAC_PYQUDA_FILES = PION_PCAC_PYQUDA_FILES
PINNED_PION_PCAC_PROPAGATOR_PYQUDA_FILES = (
    "examples/4_Pion_PCAC.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
)
MESON_SPEC_PYQUDA_FILES = (
    "tests/test_mesonspec.py",
    "tests/test_mesonspec.ini.xml",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
    "pyquda_utils/phase.py",
)

PINNED_MESON_SPEC_PYQUDA_FILES = MESON_SPEC_PYQUDA_FILES
PINNED_MESON_SPEC_PROPAGATOR_PYQUDA_FILES = (
    "tests/test_mesonspec.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
    "pyquda_utils/phase.py",
)
RHO_VECTOR_PYQUDA_FILES = (
    "tests/test_mesonspec.py",
    "tests/test_mesonspec.ini.xml",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
)
PINNED_RHO_VECTOR_PYQUDA_FILES = RHO_VECTOR_PYQUDA_FILES
PINNED_RHO_VECTOR_PROPAGATOR_PYQUDA_FILES = (
    "tests/test_mesonspec.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
)
PROTON_2PT_PYQUDA_FILES = (
    "examples/3_Pion_Proton_2pt.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/source.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
)

PINNED_PROTON_2PT_PYQUDA_FILES = PROTON_2PT_PYQUDA_FILES
PINNED_PROTON_2PT_PROPAGATOR_PYQUDA_FILES = (
    "examples/3_Pion_Proton_2pt.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
    "pyquda_utils/source.py",
)
QUARK_PROPAGATOR_PYQUDA_FILES = (
    "examples/2_Quark_Propagator.py",
    "tests/test_gaussian.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/source.py",
    "pyquda_utils/core.py",
)
PINNED_QUARK_PROPAGATOR_PYQUDA_FILES = QUARK_PROPAGATOR_PYQUDA_FILES
PINNED_GAUSSIAN_SHELL_QUARK_PROPAGATOR_PYQUDA_FILES = (
    "tests/test_gaussian.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/source.py",
    "pyquda_utils/core.py",
    "examples/2_Quark_Propagator.py",
)
APE_SMEAR_PYQUDA_FILES = (
    "tests/test_smear.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
)
PINNED_APE_SMEAR_PYQUDA_FILES = APE_SMEAR_PYQUDA_FILES
HYP_SMEAR_PYQUDA_FILES = (
    "tests/test_smear.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
)
PINNED_HYP_SMEAR_PYQUDA_FILES = HYP_SMEAR_PYQUDA_FILES
WILSON_FLOW_PYQUDA_FILES = (
    "tests/test_wflow.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
)
PINNED_WILSON_FLOW_PYQUDA_FILES = WILSON_FLOW_PYQUDA_FILES
STOUT_SMEAR_PYQUDA_FILES = (
    "tests/test_smear.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
)
PINNED_STOUT_SMEAR_PYQUDA_FILES = STOUT_SMEAR_PYQUDA_FILES


@dataclass
class RepoDocument:
    source: str
    path: str
    text: str


def _read_file(path: Path, max_chars: int = 4000) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]


def collect_documents(*, workspace_root: Path, pyquda_repo: Path, task_type: str) -> list[RepoDocument]:
    docs: list[RepoDocument] = []
    for rel_path in WORKFLOW_FILES:
        path = workspace_root / rel_path
        if path.exists():
            docs.append(RepoDocument(source="workspace", path=str(path), text=_read_file(path)))
    if task_type == "pion_2pt":
        for rel_path in PION_2PT_PYQUDA_FILES:
            path = pyquda_repo / rel_path
            if path.exists():
                docs.append(RepoDocument(source="pyquda", path=str(path), text=_read_file(path)))
    if task_type == "pion_dispersion":
        for rel_path in PION_DISPERSION_PYQUDA_FILES:
            path = pyquda_repo / rel_path
            if path.exists():
                docs.append(RepoDocument(source="pyquda", path=str(path), text=_read_file(path)))
    if task_type == "pion_pcac":
        for rel_path in PION_PCAC_PYQUDA_FILES:
            path = pyquda_repo / rel_path
            if path.exists():
                docs.append(RepoDocument(source="pyquda", path=str(path), text=_read_file(path)))
    if task_type == "meson_spec":
        for rel_path in MESON_SPEC_PYQUDA_FILES:
            path = pyquda_repo / rel_path
            if path.exists():
                docs.append(RepoDocument(source="pyquda", path=str(path), text=_read_file(path)))
    if task_type == "rho_vector":
        for rel_path in RHO_VECTOR_PYQUDA_FILES:
            path = pyquda_repo / rel_path
            if path.exists():
                docs.append(RepoDocument(source="pyquda", path=str(path), text=_read_file(path)))
    if task_type == "proton_2pt":
        for rel_path in PROTON_2PT_PYQUDA_FILES:
            path = pyquda_repo / rel_path
            if path.exists():
                docs.append(RepoDocument(source="pyquda", path=str(path), text=_read_file(path)))
    if task_type == "quark_propagator":
        for rel_path in QUARK_PROPAGATOR_PYQUDA_FILES:
            path = pyquda_repo / rel_path
            if path.exists():
                docs.append(RepoDocument(source="pyquda", path=str(path), text=_read_file(path)))
    if task_type == "ape_smear":
        for rel_path in APE_SMEAR_PYQUDA_FILES:
            path = pyquda_repo / rel_path
            if path.exists():
                docs.append(RepoDocument(source="pyquda", path=str(path), text=_read_file(path)))
    if task_type == "hyp_smear":
        for rel_path in HYP_SMEAR_PYQUDA_FILES:
            path = pyquda_repo / rel_path
            if path.exists():
                docs.append(RepoDocument(source="pyquda", path=str(path), text=_read_file(path)))
    if task_type == "wilson_flow":
        for rel_path in WILSON_FLOW_PYQUDA_FILES:
            path = pyquda_repo / rel_path
            if path.exists():
                docs.append(RepoDocument(source="pyquda", path=str(path), text=_read_file(path)))
    if task_type == "stout_smear":
        for rel_path in STOUT_SMEAR_PYQUDA_FILES:
            path = pyquda_repo / rel_path
            if path.exists():
                docs.append(RepoDocument(source="pyquda", path=str(path), text=_read_file(path)))
    return docs
