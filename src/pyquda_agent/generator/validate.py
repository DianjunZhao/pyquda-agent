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
        "def _load_runtime_modules():",
        "from pyquda_utils import core, gamma, io",
        "import cupy as cp",
        "import numpy as np",
        "core.getClover",
        'core.invert(dirac, "wall", t_src)',
        "io.readQIOGauge",
        "core.gatherLattice",
        "np.save",
    ]
    missing = [token for token in required_tokens if token not in code]
    if missing:
        raise ValueError(f"Generated script is missing required tokens: {', '.join(missing)}")
