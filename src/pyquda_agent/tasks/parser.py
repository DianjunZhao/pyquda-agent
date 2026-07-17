"""Natural-language parser for the current narrow supported PyQUDA workflows."""

from __future__ import annotations

import re

from .schema import Pion2ptTaskDraft


PATH_RE = re.compile(r"([A-Za-z0-9_./~:-]+\.(?:lime|xml|h5|hdf5|npy|npz|dat|json))")
RESOURCE_TOKEN_RE = re.compile(r"(~?[A-Za-z0-9_./:-]+)")
VECTOR_RE = re.compile(r"\[\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\]")
LATTICE_RE = re.compile(r"(?:lattice|latt(?:ice)? size)\s*(?:=|:)?\s*\[?\s*(\d+)\s*[,\sxX]+\s*(\d+)\s*[,\sxX]+\s*(\d+)\s*[,\sxX]+\s*(\d+)")
GRID_RE = re.compile(r"(?:grid|grid size)\s*(?:=|:)?\s*\[?\s*(\d+)\s*[,\sxX]+\s*(\d+)\s*[,\sxX]+\s*(\d+)\s*[,\sxX]+\s*(\d+)")
CLUSTER_RE = re.compile(r"(?:cluster_launch|cluster)\s*(?:=|:)?\s*([A-Za-z0-9_.:-]+)", re.IGNORECASE)
SOURCE_PATTERNS = {
    "wall": re.compile(r"(?:\bwall\s+source\b|\bsource(?:\s+type)?\s*(?:=|:)?\s*wall\b)", re.IGNORECASE),
    "point": re.compile(r"(?:\bpoint\s+source\b|\bsource(?:\s+type)?\s*(?:=|:)?\s*point\b)", re.IGNORECASE),
    "volume": re.compile(r"(?:\bvolume\s+source\b|\bsource(?:\s+type)?\s*(?:=|:)?\s*volume\b)", re.IGNORECASE),
}
SINK_PATTERNS = {
    "local": re.compile(r"(?:\blocal\s+sink\b|\bsink(?:\s+type)?\s*(?:=|:)?\s*local\b)", re.IGNORECASE),
    "smeared": re.compile(r"(?:\bsmeared\s+sink\b|\bsink(?:\s+type)?\s*(?:=|:)?\s*smeared\b)", re.IGNORECASE),
}
FLOAT_FIELDS = {
    "mass": re.compile(r"(?:mass)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE),
    "xi_0": re.compile(r"(?:xi_0|xi0)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE),
    "nu": re.compile(r"(?:nu)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE),
    "coeff_t": re.compile(r"(?:coeff_t)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE),
    "coeff_r": re.compile(r"(?:coeff_r)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE),
    "solver_tol": re.compile(r"(?:tol|solver_tol)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE),
    "flow_epsilon": re.compile(r"(?:flow[_ -]?epsilon|epsilon)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE),
    "stout_smear_rho": re.compile(r"(?:stout(?:[_ -]?smear)?[_ -]?rho|stout rho)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE),
    "source_smearing_rho": re.compile(r"(?:gaussian(?:[_ -]?smear)?[_ -]?rho|gaussian rho|shell[_ -]?rho)\s*(?:=|:)?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE),
}
INT_FIELDS = {
    "solver_maxiter": re.compile(r"(?:maxiter|max_iter|solver_maxiter)\s*(?:=|:)?\s*(\d+)", re.IGNORECASE),
    "flow_steps": re.compile(r"(?:flow[_ -]?steps|steps)\s*(?:=|:)?\s*(\d+)", re.IGNORECASE),
    "stout_smear_steps": re.compile(r"(?:stout(?:[_ -]?smear)?[_ -]?steps|stout steps)\s*(?:=|:)?\s*(\d+)", re.IGNORECASE),
    "stout_smear_ndim": re.compile(r"(?:stout(?:[_ -]?smear)?[_ -]?(?:ndim|dir[_ -]?ignore)|stout dir[_ -]?ignore)\s*(?:=|:)?\s*(\d+)", re.IGNORECASE),
    "source_smearing_steps": re.compile(r"(?:gaussian(?:[_ -]?smear)?[_ -]?steps|gaussian steps|shell[_ -]?steps)\s*(?:=|:)?\s*(\d+)", re.IGNORECASE),
}
TIMESLICE_RE = re.compile(r"(?:timeslice|t_src|source time|source timeslice)\s*(?:=|:)?\s*(\d+)", re.IGNORECASE)
ZERO_MOMENTUM_RE = re.compile(r"(?:\bzero\s+momentum\b|零动量)", re.IGNORECASE)
NONZERO_MOMENTUM_RE = re.compile(r"(?:\bnonzero\s+momentum\b|\bnon-zero\s+momentum\b)", re.IGNORECASE)
GAUSSIAN_SHELL_SOURCE_RE = re.compile(r"(?:\bgaussian(?:-|\s)?(?:shell|smeared?)\b|\bshell(?:-|\s)?source\b)", re.IGNORECASE)


def _maybe_set_source(draft: Pion2ptTaskDraft, field_name: str, source: str) -> None:
    if getattr(draft, field_name) not in (None, [], {}):
        draft.field_sources[field_name] = source


def _record_user_field(draft: Pion2ptTaskDraft, field_name: str) -> None:
    value = getattr(draft, field_name)
    if value not in (None, [], {}):
        draft.user_confirmed_fields[field_name] = value


def _record_parser_guess(draft: Pion2ptTaskDraft, field_name: str) -> None:
    value = getattr(draft, field_name)
    if value not in (None, [], {}):
        draft.parser_guesses[field_name] = value


def _parse_output_path(text: str) -> str | None:
    match = re.search(r"([A-Za-z0-9_./~:-]+\.py)", text)
    if match:
        return match.group(1)
    return None


def _is_output_like_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith(("outputs/", "./outputs/", "data/", "./data/")):
        return True
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    return "outputs" in parts or "data" in parts


def _parse_output_data_path(text: str) -> tuple[str | None, str | None]:
    explicit = re.search(
        r"(?:^|[\s,;])(?:output|输出|correlator output)(?:\s+path)?(?:\s*(?:=|:)\s*|\s+)([A-Za-z0-9_./~:-]+\.(?:npy|h5|hdf5))",
        text,
        re.IGNORECASE,
    )
    if explicit:
        path = explicit.group(1)
    else:
        matches = re.findall(r"([A-Za-z0-9_./~:-]+\.(?:npy|h5|hdf5))", text)
        output_like = [path for path in matches if _is_output_like_path(path)]
        if not output_like:
            return None, None
        path = output_like[-1]
    if path.endswith(".npy"):
        return "npy", path
    return "hdf5", path


def _parse_propagator_paths(text: str) -> list[str]:
    paths = [path for path in PATH_RE.findall(text) if path.endswith((".npy", ".h5", ".hdf5", ".dat"))]
    lowered = text.lower()
    if "qio propagator" in lowered or "chroma qio propagator" in lowered:
        match = re.search(
            r"(?:qio propagator|chroma qio propagator)\s*(?:at|from|path)?\s*([A-Za-z0-9_./~:-]+)",
            text,
            re.IGNORECASE,
        )
        if match:
            candidate = match.group(1)
            if "/" in candidate or candidate.startswith("~"):
                paths.append(candidate)
    deduped: list[str] = []
    for path in paths:
        if path not in deduped:
            deduped.append(path)
    return deduped


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


def _strip_output_paths_from_propagators(
    paths: list[str],
    *,
    correlator_output_path: str | None,
    script_output_path: str | None,
) -> list[str]:
    excluded = {path for path in (correlator_output_path, script_output_path) if path}
    return [path for path in paths if path not in excluded]


def parse_task_description(task_description: str) -> Pion2ptTaskDraft:
    lowered = task_description.lower()
    draft = Pion2ptTaskDraft()
    draft.user_request = task_description.strip()
    draft.notes = task_description.strip()

    if "pion" in lowered and ("dispersion" in lowered or "nonzero momentum" in lowered or "non-zero momentum" in lowered):
        draft.task_type = "pion_dispersion"
        draft.field_sources["task_type"] = "parser_guess"
        _record_parser_guess(draft, "task_type")
    elif "pion" in lowered and "pcac" in lowered:
        draft.task_type = "pion_pcac"
        draft.field_sources["task_type"] = "parser_guess"
        _record_parser_guess(draft, "task_type")
    elif (
        "meson spectrum" in lowered
        or "meson spectroscopy" in lowered
        or "mesonspec" in lowered
        or "gamma5 meson" in lowered
        or "gamma4gamma5 meson" in lowered
    ):
        draft.task_type = "meson_spec"
        draft.field_sources["task_type"] = "parser_guess"
        _record_parser_guess(draft, "task_type")
    elif (
        ("rho" in lowered or "vector meson" in lowered or "vector channel" in lowered)
        and ("2pt" in lowered or "two-point" in lowered or "two point" in lowered or "correlator" in lowered)
    ):
        draft.task_type = "rho_vector"
        draft.field_sources["task_type"] = "parser_guess"
        _record_parser_guess(draft, "task_type")
    elif "quark propagator" in lowered or "point-source propagator" in lowered or "point source propagator" in lowered:
        draft.task_type = "quark_propagator"
        draft.field_sources["task_type"] = "parser_guess"
        _record_parser_guess(draft, "task_type")
    elif "wilson flow" in lowered or "gradient flow" in lowered:
        draft.task_type = "wilson_flow"
        draft.field_sources["task_type"] = "parser_guess"
        _record_parser_guess(draft, "task_type")
    elif "ape" in lowered and "smear" in lowered and "gauge" in lowered:
        draft.task_type = "ape_smear"
        draft.field_sources["task_type"] = "parser_guess"
        _record_parser_guess(draft, "task_type")
    elif "hyp" in lowered and "smear" in lowered and "gauge" in lowered:
        draft.task_type = "hyp_smear"
        draft.field_sources["task_type"] = "parser_guess"
        _record_parser_guess(draft, "task_type")
    elif "stout" in lowered and "smear" in lowered and "gauge" in lowered:
        draft.task_type = "stout_smear"
        draft.field_sources["task_type"] = "parser_guess"
        _record_parser_guess(draft, "task_type")
    elif ("proton" in lowered or "nucleon" in lowered) and ("2pt" in lowered or "two-point" in lowered or "two point" in lowered):
        draft.task_type = "proton_2pt"
        draft.field_sources["task_type"] = "parser_guess"
        _record_parser_guess(draft, "task_type")
    elif "pion" in lowered and ("2pt" in lowered or "two-point" in lowered or "two point" in lowered):
        draft.task_type = "pion_2pt"
        draft.field_sources["task_type"] = "parser_guess"
        _record_parser_guess(draft, "task_type")

    if "from gauge" in lowered or "gauge configuration" in lowered or "从 gauge" in lowered:
        draft.start_from = "gauge"
        draft.has_existing_propagators = False
        draft.field_sources["start_from"] = "parsed"
        draft.field_sources["has_existing_propagators"] = "parsed"
        _record_user_field(draft, "start_from")
        _record_user_field(draft, "has_existing_propagators")
    elif (
        "existing propagator" in lowered
        or "existing chroma qio propagator" in lowered
        or "existing qio propagator" in lowered
        or "已有 propagator" in lowered
        or "读取 propagator" in lowered
        or "from propagator" in lowered
    ):
        draft.start_from = "propagator"
        draft.has_existing_propagators = True
        draft.field_sources["start_from"] = "parsed"
        draft.field_sources["has_existing_propagators"] = "parsed"
        _record_user_field(draft, "start_from")
        _record_user_field(draft, "has_existing_propagators")

    paths = [match for match in PATH_RE.findall(task_description)]
    for path in paths:
        if path.endswith((".lime", ".xml")) and draft.gauge_path is None:
            draft.gauge_path = path
            draft.gauge_format = "chroma_qio"
        elif draft.start_from != "propagator" and path.endswith((".npy", ".h5", ".hdf5")):
            draft.correlator_output_path = path
    if draft.start_from == "propagator":
        draft.propagator_paths = _parse_propagator_paths(task_description)
        if draft.propagator_paths:
            draft.field_sources["propagator_paths"] = "parsed"
            draft.propagator_format = _infer_propagator_format(draft.propagator_paths, lowered)
            _maybe_set_source(draft, "propagator_format", "parsed")
            _record_user_field(draft, "propagator_paths")
            _record_user_field(draft, "propagator_format")
    _maybe_set_source(draft, "gauge_path", "parsed")
    if draft.gauge_format is not None:
        draft.field_sources["gauge_format"] = "parser_guess"
        _record_parser_guess(draft, "gauge_format")
    _record_user_field(draft, "gauge_path")

    source_type = None
    for value, pattern in SOURCE_PATTERNS.items():
        if pattern.search(task_description):
            source_type = value
            break
    if source_type:
        draft.source_type = source_type
        draft.field_sources["source_type"] = "parsed"
        _record_user_field(draft, "source_type")

    for value, pattern in SINK_PATTERNS.items():
        if pattern.search(task_description):
            draft.sink_type = value
            draft.field_sources["sink_type"] = "parsed"
            _record_user_field(draft, "sink_type")
            break

    if draft.task_type == "quark_propagator" and GAUSSIAN_SHELL_SOURCE_RE.search(task_description):
        draft.source_smearing_kind = "gaussian_shell"
        draft.field_sources["source_smearing_kind"] = "parsed"
        _record_user_field(draft, "source_smearing_kind")

    if ZERO_MOMENTUM_RE.search(task_description) and not NONZERO_MOMENTUM_RE.search(task_description):
        draft.momentum_projection = "zero"
        draft.momenta = [[0, 0, 0]]
        draft.field_sources["momentum_projection"] = "parsed"
        draft.field_sources["momenta"] = "parsed"
        _record_user_field(draft, "momentum_projection")
        _record_user_field(draft, "momenta")
    elif "momentum" in lowered or "动量" in lowered:
        draft.momentum_projection = "explicit"
        draft.momenta = [[int(a), int(b), int(c)] for a, b, c in VECTOR_RE.findall(task_description)]
        draft.field_sources["momentum_projection"] = "parsed"
        _maybe_set_source(draft, "momenta", "parsed")
        _record_user_field(draft, "momentum_projection")
        _record_user_field(draft, "momenta")

    timeslices = [int(value) for value in TIMESLICE_RE.findall(task_description)]
    if timeslices:
        draft.source_timeslices = timeslices
        draft.field_sources["source_timeslices"] = "parsed"
        _record_user_field(draft, "source_timeslices")

    lattice_match = LATTICE_RE.search(task_description)
    if lattice_match:
        draft.lattice_size = [int(value) for value in lattice_match.groups()]
        draft.field_sources["lattice_size"] = "parsed"
        _record_user_field(draft, "lattice_size")

    grid_match = GRID_RE.search(task_description)
    if grid_match:
        draft.grid_size = [int(value) for value in grid_match.groups()]
        draft.field_sources["grid_size"] = "parsed"
        _record_user_field(draft, "grid_size")

    for field_name, pattern in FLOAT_FIELDS.items():
        match = pattern.search(task_description)
        if match:
            setattr(draft, field_name, float(match.group(1)))
            draft.field_sources[field_name] = "parsed"
            _record_user_field(draft, field_name)
    for field_name, pattern in INT_FIELDS.items():
        match = pattern.search(task_description)
        if match:
            setattr(draft, field_name, int(match.group(1)))
            draft.field_sources[field_name] = "parsed"
            _record_user_field(draft, field_name)

    if "clover" in lowered:
        draft.fermion_action = "clover"
        draft.field_sources["fermion_action"] = "parsed"
        _record_user_field(draft, "fermion_action")

    if "without gauge fixing" in lowered or "not gauge fixed" in lowered or "not gauge-fixed" in lowered:
        draft.gauge_fixed = False
        draft.field_sources["gauge_fixed"] = "parsed"
        _record_user_field(draft, "gauge_fixed")
    elif "gauge fixed" in lowered or "gauge fixing" in lowered or "gauge-fixed" in lowered:
        draft.gauge_fixed = True
        draft.field_sources["gauge_fixed"] = "parsed"
        _record_user_field(draft, "gauge_fixed")

    output_format, output_path = _parse_output_data_path(task_description)
    if output_format:
        draft.correlator_output_format = output_format
        draft.correlator_output_path = output_path
        draft.field_sources["correlator_output_format"] = "parsed"
        draft.field_sources["correlator_output_path"] = "parsed"
        _record_user_field(draft, "correlator_output_format")
        _record_user_field(draft, "correlator_output_path")

    script_output_path = _parse_output_path(task_description)
    if script_output_path:
        draft.script_output_path = script_output_path
        draft.field_sources["script_output_path"] = "parsed"
        _record_user_field(draft, "script_output_path")

    if draft.start_from == "propagator" and draft.propagator_paths:
        draft.propagator_paths = _strip_output_paths_from_propagators(
            draft.propagator_paths,
            correlator_output_path=draft.correlator_output_path,
            script_output_path=draft.script_output_path,
        )
        if draft.propagator_paths:
            draft.user_confirmed_fields["propagator_paths"] = list(draft.propagator_paths)

    if "complete" in lowered or "完整可运行" in lowered:
        draft.script_style = "complete"
        draft.field_sources["script_style"] = "parsed"
        _record_user_field(draft, "script_style")
    elif "template" in lowered or "模板" in lowered:
        draft.script_style = "template"
        draft.field_sources["script_style"] = "parsed"
        _record_user_field(draft, "script_style")

    if "resource_path" in lowered:
        match = re.search(r"resource_path\s*(?:=|:)?\s*([A-Za-z0-9_./~:-]+)", task_description)
        if match:
            draft.resource_path = match.group(1)
            draft.field_sources["resource_path"] = "parsed"
            _record_user_field(draft, "resource_path")

    cluster_match = CLUSTER_RE.search(task_description)
    if cluster_match:
        draft.cluster_launch = cluster_match.group(1)
        draft.field_sources["cluster_launch"] = "parsed"
        _record_user_field(draft, "cluster_launch")
    elif "slurm" in lowered:
        draft.cluster_launch = "slurm"
        draft.field_sources["cluster_launch"] = "parsed"
        _record_user_field(draft, "cluster_launch")
    elif "mpirun" in lowered or "srun" in lowered:
        draft.cluster_launch = "mpi"
        draft.field_sources["cluster_launch"] = "parsed"
        _record_user_field(draft, "cluster_launch")
    elif "local" in lowered and "cluster" in lowered:
        draft.cluster_launch = "local"
        draft.field_sources["cluster_launch"] = "parsed"
        _record_user_field(draft, "cluster_launch")
    elif "cluster" in lowered or "hpc" in lowered:
        draft.cluster_launch = "hpc"
        draft.field_sources["cluster_launch"] = "parsed"
        _record_user_field(draft, "cluster_launch")

    return draft
