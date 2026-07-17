"""Minimal validation for generated scripts."""

from __future__ import annotations

import ast


def validate_generated_script(code: str) -> None:
    ast.parse(code)
    forbidden_tokens = ["TODO", "pass", "placeholder", "fake_", "mock_"]
    hits = [token for token in forbidden_tokens if token in code]
    if hits:
        raise ValueError(f"Generated script still contains forbidden placeholder markers: {', '.join(hits)}")
    required_tokens = [
        "def _validate_handoff_contract() -> None:",
        "TASK_ARTIFACT = SCRIPT_PATH.with_suffix(\".task.json\")",
        "PHYSICS_ARTIFACT = SCRIPT_PATH.with_suffix(\".physics.json\")",
        "PLAN_ARTIFACT = SCRIPT_PATH.with_suffix(\".plan.json\")",
        "PROBE_ARTIFACT = SCRIPT_PATH.with_suffix(\".probe.json\")",
        "RESOURCE_PATH =",
        "CLUSTER_LAUNCH =",
        "def _load_runtime_modules():",
        "import cupy as cp",
        "import numpy as np",
        "Launch assumption:",
        "QUDA resource path assumption:",
        "Probe artifact path:",
        "Output contract:",
        "_validate_handoff_contract()",
        "_print_handoff_summary()",
    ]
    missing = [token for token in required_tokens if token not in code]
    if missing:
        raise ValueError(f"Generated script is missing required tokens: {', '.join(missing)}")
    has_dirac_builder = "core.getClover" in code or "core.getDirac" in code
    has_propagator_entry = "PROPAGATOR_PATHS" in code and ("io.readNPYPropagator" in code or "io.readQIOPropagator" in code or "core.LatticePropagator.loadH5" in code)
    has_wilson_flow = "wilsonFlowChroma" in code
    has_ape_smear = "apeSmearChroma(" in code
    has_hyp_smear = "hypSmear(" in code
    has_stout_smear = "stoutSmear(" in code
    if not has_dirac_builder and not has_propagator_entry and not has_wilson_flow and not has_ape_smear and not has_hyp_smear and not has_stout_smear:
        raise ValueError("Generated script is missing a supported Dirac-operator construction call.")
    if "io.readQIOGauge" not in code and "io.readChromaQIOGauge" not in code and not has_propagator_entry:
        raise ValueError("Generated script is missing a supported gauge IO call.")
    if (
        "from pyquda_utils import core, gamma, io" not in code
        and "from pyquda_utils import core, gamma, io, phase" not in code
        and "from pyquda_utils import core, io, source" not in code
        and "from pyquda_utils import core, io" not in code
    ):
        raise ValueError("Generated script is missing the expected pyquda_utils imports.")
    has_output_write = "np.save" in code or ".saveH5(" in code or "io.writeNPYGauge" in code
    if not has_output_write:
        raise ValueError("Generated script is missing a grounded output-write call.")
    if "core.gatherLattice" not in code and ".saveH5(" not in code and "io.writeNPYGauge" not in code and not has_wilson_flow:
        raise ValueError("Generated script is missing a supported result persistence path.")
    if (
        'core.invert(dirac, "wall", t_src)' not in code
        and 'core.invert(dirac, "point", [SOURCE_SPATIAL_ORIGIN[0], SOURCE_SPATIAL_ORIGIN[1], SOURCE_SPATIAL_ORIGIN[2], t_src])' not in code
        and "dirac.invert(b)" not in code
        and "core.invertPropagator" not in code
        and not has_propagator_entry
        and not has_wilson_flow
        and not has_ape_smear
        and not has_hyp_smear
        and not has_stout_smear
    ):
        raise ValueError("Generated script is missing a supported invert call for the chosen workflow.")
