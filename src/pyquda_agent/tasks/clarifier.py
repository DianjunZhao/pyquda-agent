"""Clarification logic for the first runnable pion 2pt workflow."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .schema import Pion2ptTaskDraft


SUPPORTED_WORKFLOW_ID = "pion_2pt_chroma_wall_local_zero_momentum_npy_v1"
SUPPORTED_ACTION = "clover"
SUPPORTED_GAUGE_FORMAT = "chroma_qio"
SUPPORTED_SOURCE = "wall"
SUPPORTED_SINK = "local"
SUPPORTED_MOMENTUM = "zero"
SUPPORTED_OUTPUT = "npy"


@dataclass
class ClarifyingQuestion:
    field_name: str
    prompt: str
    category: str


QUESTION_ORDER = (
    ("start_from", "这第一版只支持从 gauge configuration 开始。请回答 gauge。", "pyquda"),
    ("has_existing_propagators", "你是否要从已有 propagator 开始？请回答 yes/no。第一版 complete mode 只支持 no。", "pyquda"),
    ("gauge_format", "gauge 文件格式是什么？第一版只支持 chroma_qio。", "pyquda"),
    ("gauge_path", "请提供 gauge 文件路径（例如 .lime）。", "runtime"),
    ("propagator_format", "如果你是从已有 propagator 开始，请提供 propagator 格式。", "runtime"),
    ("propagator_paths", "如果你是从已有 propagator 开始，请提供 propagator 路径。", "runtime"),
    ("lattice_size", "请提供 lattice size，例如 24 24 24 72。", "runtime"),
    ("grid_size", "请提供 QUDA/MPI grid size，例如 1 1 1 2。", "runtime"),
    ("fermion_action", "请提供 fermion action。第一版只支持 clover。", "physics"),
    ("mass", "请提供 mass 参数。", "physics"),
    ("xi_0", "请提供 xi_0 参数。", "physics"),
    ("nu", "请提供 nu 参数。", "physics"),
    ("coeff_t", "请提供 coeff_t 参数。", "physics"),
    ("coeff_r", "请提供 coeff_r 参数。", "physics"),
    ("solver_tol", "请提供 solver tolerance，例如 1e-12。", "pyquda"),
    ("solver_maxiter", "请提供 solver maxiter，例如 1000。", "pyquda"),
    ("source_type", "source 类型是什么？第一版只支持 wall。", "physics"),
    ("sink_type", "sink 类型是什么？第一版只支持 local。", "physics"),
    ("momentum_projection", "动量投影是什么？第一版只支持 zero。", "physics"),
    ("source_timeslices", "请提供 source timeslice，例如 0。", "physics"),
    ("gauge_fixed", "是否已做 gauge fixing？请回答 yes/no。", "physics"),
    ("correlator_output_format", "输出格式是什么？第一版只支持 npy。", "runtime"),
    ("correlator_output_path", "请提供 correlator 输出路径，例如 outputs/pion_twopt.npy。", "runtime"),
    ("resource_path", "请提供 QUDA resource_path，例如 .cache/quda。", "runtime"),
    ("cluster_launch", "请提供集群/运行假设，例如 local、mpi、slurm。", "runtime"),
    ("script_output_path", "请提供最终 Python 脚本输出路径。", "runtime"),
    ("script_style", "请回答 complete。第一版 complete mode 才会生成真实脚本。", "runtime"),
)


def _record_unsupported(draft: Pion2ptTaskDraft, reason: str) -> None:
    if reason not in draft.unsupported_reasons:
        draft.unsupported_reasons.append(reason)


def determine_missing_fields(draft: Pion2ptTaskDraft) -> list[str]:
    missing: list[str] = []
    draft.unsupported_reasons = []

    if draft.task_type != "pion_2pt":
        missing.append("task_type")
    if draft.workflow_id != SUPPORTED_WORKFLOW_ID:
        missing.append("workflow_id")

    if draft.start_from is None:
        missing.append("start_from")
    elif draft.start_from != "gauge":
        _record_unsupported(draft, "First version only supports starting from a gauge configuration.")

    if draft.has_existing_propagators is None:
        missing.append("has_existing_propagators")
    elif draft.has_existing_propagators:
        _record_unsupported(draft, "First version does not support starting from existing propagators.")
        if draft.propagator_format is None:
            missing.append("propagator_format")
        if not draft.propagator_paths:
            missing.append("propagator_paths")

    if draft.gauge_format is None:
        missing.append("gauge_format")
    elif draft.gauge_format != SUPPORTED_GAUGE_FORMAT:
        _record_unsupported(draft, "First version only supports Chroma/QIO gauge input.")

    if not draft.gauge_path:
        missing.append("gauge_path")
    if not draft.lattice_size:
        missing.append("lattice_size")
    if not draft.grid_size:
        missing.append("grid_size")

    if draft.fermion_action is None:
        missing.append("fermion_action")
    elif draft.fermion_action != SUPPORTED_ACTION:
        _record_unsupported(draft, "First version only supports Clover fermion action.")

    for field_name in ("mass", "xi_0", "nu", "coeff_t", "coeff_r", "solver_tol", "solver_maxiter"):
        if getattr(draft, field_name) is None:
            missing.append(field_name)

    if draft.source_type is None:
        missing.append("source_type")
    elif draft.source_type != SUPPORTED_SOURCE:
        _record_unsupported(draft, "First version only supports wall source.")

    if draft.sink_type is None:
        missing.append("sink_type")
    elif draft.sink_type != SUPPORTED_SINK:
        _record_unsupported(draft, "First version only supports local sink.")

    if draft.momentum_projection is None:
        missing.append("momentum_projection")
    elif draft.momentum_projection != SUPPORTED_MOMENTUM:
        _record_unsupported(draft, "First version only supports zero-momentum pion 2pt.")

    if draft.momentum_projection == SUPPORTED_MOMENTUM and draft.momenta != [[0, 0, 0]]:
        _record_unsupported(draft, "Zero-momentum workflow requires momenta == [[0, 0, 0]].")
    elif not draft.momenta:
        missing.append("momenta")

    if not draft.source_timeslices:
        missing.append("source_timeslices")
    if draft.gauge_fixed is None:
        missing.append("gauge_fixed")

    if draft.correlator_output_format is None:
        missing.append("correlator_output_format")
    elif draft.correlator_output_format != SUPPORTED_OUTPUT:
        _record_unsupported(draft, "First version only supports .npy correlator output.")

    if not draft.correlator_output_path:
        missing.append("correlator_output_path")
    if not draft.resource_path:
        missing.append("resource_path")
    if not draft.cluster_launch:
        missing.append("cluster_launch")
    if not draft.script_output_path:
        missing.append("script_output_path")

    if draft.script_style is None:
        missing.append("script_style")
    elif draft.script_style != "complete":
        _record_unsupported(draft, "This workflow only supports complete mode for runnable output.")

    draft.missing_fields = missing
    return missing


def build_questions(draft: Pion2ptTaskDraft, max_questions: int) -> list[ClarifyingQuestion]:
    missing = set(determine_missing_fields(draft))
    questions: list[ClarifyingQuestion] = []
    for field_name, prompt, category in QUESTION_ORDER:
        if field_name in missing:
            questions.append(ClarifyingQuestion(field_name=field_name, prompt=prompt, category=category))
        if len(questions) >= max_questions:
            break
    return questions


def _parse_bool(answer: str) -> bool | None:
    lowered = answer.strip().lower()
    if lowered in {"yes", "y", "true", "是", "已做"}:
        return True
    if lowered in {"no", "n", "false", "否", "未做"}:
        return False
    return None


def _parse_int_list(answer: str) -> list[int]:
    return [int(item) for item in re.findall(r"-?\d+", answer)]


def _parse_path_list(answer: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_./~:-]+\.(?:lime|xml|h5|hdf5|npy|npz|dat|json)", answer)


def apply_answer(draft: Pion2ptTaskDraft, field_name: str, answer: str) -> None:
    value = answer.strip()
    draft.field_sources[field_name] = "clarified"
    if field_name == "start_from":
        draft.start_from = value.lower()
        draft.has_existing_propagators = value.lower() == "propagator"
        draft.field_sources["has_existing_propagators"] = "clarified"
    elif field_name == "has_existing_propagators":
        parsed = _parse_bool(value)
        if parsed is not None:
            draft.has_existing_propagators = parsed
            if parsed:
                draft.start_from = "propagator"
                draft.field_sources["start_from"] = "clarified"
            elif draft.start_from is None:
                draft.start_from = "gauge"
                draft.field_sources["start_from"] = "clarified"
    elif field_name == "gauge_format":
        draft.gauge_format = value.lower()
    elif field_name == "gauge_path":
        draft.gauge_path = value
    elif field_name == "propagator_format":
        draft.propagator_format = value.lower()
    elif field_name == "propagator_paths":
        draft.propagator_paths = _parse_path_list(value)
    elif field_name == "lattice_size":
        draft.lattice_size = _parse_int_list(value)
    elif field_name == "grid_size":
        draft.grid_size = _parse_int_list(value)
    elif field_name == "fermion_action":
        draft.fermion_action = value.lower()
    elif field_name in {"mass", "xi_0", "nu", "coeff_t", "coeff_r", "solver_tol"}:
        setattr(draft, field_name, float(value))
    elif field_name == "solver_maxiter":
        draft.solver_maxiter = int(value)
    elif field_name == "source_type":
        draft.source_type = value.lower()
    elif field_name == "sink_type":
        draft.sink_type = value.lower()
    elif field_name == "momentum_projection":
        draft.momentum_projection = value.lower()
        if draft.momentum_projection == "zero":
            draft.momenta = [[0, 0, 0]]
            draft.field_sources["momenta"] = "fixed"
    elif field_name == "source_timeslices":
        draft.source_timeslices = _parse_int_list(value)
    elif field_name == "gauge_fixed":
        parsed = _parse_bool(value)
        if parsed is not None:
            draft.gauge_fixed = parsed
    elif field_name == "correlator_output_format":
        draft.correlator_output_format = value.lower()
    elif field_name == "correlator_output_path":
        draft.correlator_output_path = value
    elif field_name == "resource_path":
        draft.resource_path = value
    elif field_name == "cluster_launch":
        draft.cluster_launch = value
    elif field_name == "script_output_path":
        draft.script_output_path = value
    elif field_name == "script_style":
        draft.script_style = value.lower()
    determine_missing_fields(draft)
