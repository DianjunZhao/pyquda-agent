"""Natural-language parser for the first runnable pion 2pt workflow."""

from __future__ import annotations

import re

from .schema import Pion2ptTaskDraft


PATH_RE = re.compile(r"([A-Za-z0-9_./~:-]+\.(?:lime|xml|h5|hdf5|npy|npz|dat|json))")
VECTOR_RE = re.compile(r"\[\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\]")
LATTICE_RE = re.compile(r"(?:lattice|latt(?:ice)? size)\s*(?:=|:)?\s*\[?\s*(\d+)\s*[,\sxX]+\s*(\d+)\s*[,\sxX]+\s*(\d+)\s*[,\sxX]+\s*(\d+)")
GRID_RE = re.compile(r"(?:grid|grid size)\s*(?:=|:)?\s*\[?\s*(\d+)\s*[,\sxX]+\s*(\d+)\s*[,\sxX]+\s*(\d+)\s*[,\sxX]+\s*(\d+)")
CLUSTER_RE = re.compile(r"(?:cluster_launch|cluster)\s*(?:=|:)?\s*([A-Za-z0-9_.:-]+)", re.IGNORECASE)
FLOAT_FIELDS = {
    "mass": re.compile(r"(?:mass)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE),
    "xi_0": re.compile(r"(?:xi_0|xi0)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE),
    "nu": re.compile(r"(?:nu)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE),
    "coeff_t": re.compile(r"(?:coeff_t)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE),
    "coeff_r": re.compile(r"(?:coeff_r)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE),
    "solver_tol": re.compile(r"(?:tol|solver_tol)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE),
}
INT_FIELDS = {
    "solver_maxiter": re.compile(r"(?:maxiter|max_iter|solver_maxiter)\s*(?:=|:)?\s*(\d+)", re.IGNORECASE),
}
TIMESLICE_RE = re.compile(r"(?:timeslice|t_src|source time|source timeslice)\s*(?:=|:)?\s*(\d+)", re.IGNORECASE)


def _maybe_set_source(draft: Pion2ptTaskDraft, field_name: str, source: str) -> None:
    if getattr(draft, field_name) not in (None, [], {}):
        draft.field_sources[field_name] = source


def _parse_output_path(text: str) -> str | None:
    match = re.search(r"([A-Za-z0-9_./~:-]+\.py)", text)
    if match:
        return match.group(1)
    return None


def _parse_output_data_path(text: str) -> tuple[str | None, str | None]:
    matches = re.findall(r"([A-Za-z0-9_./~:-]+\.(?:npy|h5|hdf5))", text)
    if not matches:
        return None, None
    path = matches[-1]
    if path.endswith(".npy"):
        return "npy", path
    return "h5", path


def _parse_propagator_paths(text: str) -> list[str]:
    return [path for path in PATH_RE.findall(text) if path.endswith((".npy", ".h5", ".hdf5", ".dat"))]


def _infer_propagator_format(paths: list[str], lowered: str) -> str | None:
    if "qio propagator" in lowered or "chroma qio propagator" in lowered:
        return "chroma_qio"
    if any(path.endswith(".npy") for path in paths):
        return "npy"
    if any(path.endswith((".h5", ".hdf5")) for path in paths):
        return "hdf5"
    if any(path.endswith(".dat") for path in paths):
        return "dat"
    return None


def parse_task_description(task_description: str) -> Pion2ptTaskDraft:
    lowered = task_description.lower()
    draft = Pion2ptTaskDraft()
    draft.notes = task_description.strip()

    if "pion" in lowered and ("2pt" in lowered or "two-point" in lowered or "two point" in lowered):
        draft.task_type = "pion_2pt"
        draft.workflow_id = "pion_2pt_chroma_wall_local_zero_momentum_npy_v1"
        draft.field_sources["task_type"] = "parsed"
        draft.field_sources["workflow_id"] = "fixed"

    if "from gauge" in lowered or "gauge configuration" in lowered or "从 gauge" in lowered:
        draft.start_from = "gauge"
        draft.has_existing_propagators = False
        draft.field_sources["start_from"] = "parsed"
        draft.field_sources["has_existing_propagators"] = "parsed"
    elif "existing propagator" in lowered or "已有 propagator" in lowered or "读取 propagator" in lowered or "from propagator" in lowered:
        draft.start_from = "propagator"
        draft.has_existing_propagators = True
        draft.field_sources["start_from"] = "parsed"
        draft.field_sources["has_existing_propagators"] = "parsed"

    paths = [match for match in PATH_RE.findall(task_description)]
    for path in paths:
        if path.endswith((".lime", ".xml")) and draft.gauge_path is None:
            draft.gauge_path = path
            draft.gauge_format = "chroma_qio"
        elif path.endswith((".npy", ".h5", ".hdf5")):
            draft.correlator_output_path = path
    if draft.start_from == "propagator":
        draft.propagator_paths = _parse_propagator_paths(task_description)
        if draft.propagator_paths:
            draft.field_sources["propagator_paths"] = "parsed"
            draft.propagator_format = _infer_propagator_format(draft.propagator_paths, lowered)
            _maybe_set_source(draft, "propagator_format", "parsed")
    _maybe_set_source(draft, "gauge_path", "parsed")
    _maybe_set_source(draft, "gauge_format", "parsed")

    source_type = None
    for value in ("wall", "point", "volume"):
        if value in lowered:
            source_type = value
            break
    if source_type:
        draft.source_type = source_type
        draft.field_sources["source_type"] = "parsed"

    if "local sink" in lowered or "local" in lowered:
        draft.sink_type = "local"
        draft.field_sources["sink_type"] = "parsed"
    elif "smeared" in lowered:
        draft.sink_type = "smeared"
        draft.field_sources["sink_type"] = "parsed"

    if "zero momentum" in lowered or "零动量" in lowered:
        draft.momentum_projection = "zero"
        draft.momenta = [[0, 0, 0]]
        draft.field_sources["momentum_projection"] = "parsed"
        draft.field_sources["momenta"] = "parsed"
    elif "momentum" in lowered or "动量" in lowered:
        draft.momentum_projection = "explicit"
        draft.momenta = [[int(a), int(b), int(c)] for a, b, c in VECTOR_RE.findall(task_description)]
        draft.field_sources["momentum_projection"] = "parsed"
        _maybe_set_source(draft, "momenta", "parsed")

    timeslices = [int(value) for value in TIMESLICE_RE.findall(task_description)]
    if timeslices:
        draft.source_timeslices = timeslices
        draft.field_sources["source_timeslices"] = "parsed"

    lattice_match = LATTICE_RE.search(task_description)
    if lattice_match:
        draft.lattice_size = [int(value) for value in lattice_match.groups()]
        draft.field_sources["lattice_size"] = "parsed"

    grid_match = GRID_RE.search(task_description)
    if grid_match:
        draft.grid_size = [int(value) for value in grid_match.groups()]
        draft.field_sources["grid_size"] = "parsed"

    for field_name, pattern in FLOAT_FIELDS.items():
        match = pattern.search(task_description)
        if match:
            setattr(draft, field_name, float(match.group(1)))
            draft.field_sources[field_name] = "parsed"
    for field_name, pattern in INT_FIELDS.items():
        match = pattern.search(task_description)
        if match:
            setattr(draft, field_name, int(match.group(1)))
            draft.field_sources[field_name] = "parsed"

    if "clover" in lowered:
        draft.fermion_action = "clover"
        draft.field_sources["fermion_action"] = "parsed"

    if "gauge fixed" in lowered or "gauge fixing" in lowered or "gauge-fixed" in lowered:
        draft.gauge_fixed = True
        draft.field_sources["gauge_fixed"] = "parsed"
    elif "without gauge fixing" in lowered or "not gauge fixed" in lowered:
        draft.gauge_fixed = False
        draft.field_sources["gauge_fixed"] = "parsed"

    output_format, output_path = _parse_output_data_path(task_description)
    if output_format:
        draft.correlator_output_format = output_format
        draft.correlator_output_path = output_path
        draft.field_sources["correlator_output_format"] = "parsed"
        draft.field_sources["correlator_output_path"] = "parsed"

    script_output_path = _parse_output_path(task_description)
    if script_output_path:
        draft.script_output_path = script_output_path
        draft.field_sources["script_output_path"] = "parsed"

    if "complete" in lowered or "完整可运行" in lowered:
        draft.script_style = "complete"
        draft.field_sources["script_style"] = "parsed"
    elif "template" in lowered or "模板" in lowered:
        draft.script_style = "template"
        draft.field_sources["script_style"] = "parsed"

    if "resource_path" in lowered:
        match = re.search(r"resource_path\s*(?:=|:)?\s*([A-Za-z0-9_./~:-]+)", task_description)
        if match:
            draft.resource_path = match.group(1)
            draft.field_sources["resource_path"] = "parsed"

    cluster_match = CLUSTER_RE.search(task_description)
    if cluster_match:
        draft.cluster_launch = cluster_match.group(1)
        draft.field_sources["cluster_launch"] = "parsed"
    elif "slurm" in lowered:
        draft.cluster_launch = "slurm"
        draft.field_sources["cluster_launch"] = "parsed"
    elif "mpirun" in lowered or "srun" in lowered:
        draft.cluster_launch = "mpi"
        draft.field_sources["cluster_launch"] = "parsed"
    elif "local" in lowered and "cluster" in lowered:
        draft.cluster_launch = "local"
        draft.field_sources["cluster_launch"] = "parsed"
    elif "cluster" in lowered or "hpc" in lowered:
        draft.cluster_launch = "hpc"
        draft.field_sources["cluster_launch"] = "parsed"

    return draft
