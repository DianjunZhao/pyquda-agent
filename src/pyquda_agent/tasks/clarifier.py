"""Implementation/runtime clarification logic for the runnable pion 2pt workflow."""

from __future__ import annotations

import re

from pyquda_agent.intent.schema import ClarifyingQuestion

from .clarification_groups import FIELD_TO_GROUP
from .schema import Pion2ptTaskDraft


PION_2PT_WORKFLOW_ID = "pion_2pt_chroma_wall_local_zero_momentum_npy_v1"
PION_2PT_PROPAGATOR_WORKFLOW_ID = "pion_2pt_existing_propagator_local_zero_momentum_npy_v1"
PION_PCAC_WORKFLOW_ID = "pion_pcac_chroma_wall_local_zero_momentum_npy_v1"
PION_PCAC_PROPAGATOR_WORKFLOW_ID = "pion_pcac_existing_propagator_local_zero_momentum_npy_v1"
PION_DISPERSION_WORKFLOW_ID = "pion_dispersion_chroma_point_momentum_npy_v1"
MESON_SPEC_WORKFLOW_ID = "meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1"
MESON_SPEC_PROPAGATOR_WORKFLOW_ID = "meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1"
PROTON_2PT_WORKFLOW_ID = "proton_2pt_chroma_wall_local_zero_momentum_npy_v1"
PROTON_2PT_PROPAGATOR_WORKFLOW_ID = "proton_2pt_existing_propagator_local_zero_momentum_npy_v1"
RHO_VECTOR_WORKFLOW_ID = "rho_vector_chroma_wall_local_zero_momentum_npy_v1"
RHO_VECTOR_PROPAGATOR_WORKFLOW_ID = "rho_vector_existing_propagator_local_zero_momentum_npy_v1"
QUARK_PROPAGATOR_WORKFLOW_ID = "quark_propagator_chroma_point_hdf5_v1"
QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID = "quark_propagator_gaussian_shell_chroma_hdf5_v1"
APE_SMEAR_WORKFLOW_ID = "ape_smear_chroma_qio_npy_v1"
HYP_SMEAR_WORKFLOW_ID = "hyp_smear_chroma_qio_npy_v1"
WILSON_FLOW_WORKFLOW_ID = "wilson_flow_chroma_qio_energy_npy_v1"
STOUT_SMEAR_WORKFLOW_ID = "stout_smear_chroma_qio_npy_v1"
PION_DISPERSION_MOMENTA = [[0, 0, 0], [0, 0, 1], [0, 1, 1], [1, 1, 1], [0, 0, 2], [0, 1, 2], [1, 1, 2], [0, 2, 2], [1, 2, 2]]
MESON_SPEC_MOMENTA = [
    [npx, npy, npz]
    for npz in range(-3, 4)
    for npy in range(-3, 4)
    for npx in range(-3, 4)
    if npx * npx + npy * npy + npz * npz <= 9
]
MESON_SPEC_GAMMA_INSERTIONS = ["gamma5_gamma5", "gamma4gamma5_gamma4gamma5"]
RHO_VECTOR_GAMMA_INSERTIONS = ["gamma1_gamma1", "gamma2_gamma2", "gamma3_gamma3"]
QUESTION_ORDER = (
    ("start_from", "任务入口是什么？请回答 gauge 或 propagator。", "physics"),
    ("gauge_fixed", "是否已做 gauge fixing？请回答 yes/no。", "physics"),
    ("source_timeslices", "请提供 source timeslice，例如 0。", "physics"),
    ("fermion_action", "请提供 fermion action；当前仅支持 clover。", "implementation"),
    ("mass", "请提供 mass 参数。", "implementation"),
    ("xi_0", "请提供 xi_0 参数。", "implementation"),
    ("nu", "请提供 nu 参数。", "implementation"),
    ("coeff_t", "请提供 coeff_t 参数。", "implementation"),
    ("coeff_r", "请提供 coeff_r 参数。", "implementation"),
    ("solver_tol", "请提供 solver tolerance，例如 1e-12。", "implementation"),
    ("solver_maxiter", "请提供 solver maxiter，例如 1000。", "implementation"),
    ("flow_steps", "请提供 Wilson flow steps，例如 100。", "implementation"),
    ("flow_epsilon", "请提供 Wilson flow epsilon，例如 1.0 或 0.01。", "implementation"),
    ("propagator_format", "请提供 propagator 格式；当前仅支持 npy、hdf5、chroma_qio。", "implementation"),
    ("gauge_path", "请提供 gauge 文件路径（例如 .lime）。", "runtime"),
    ("propagator_paths", "请提供一个或多个 propagator 路径。", "runtime"),
    ("lattice_size", "请提供 lattice size，例如 24 24 24 72。", "runtime"),
    ("grid_size", "请提供 QUDA/MPI grid size，例如 1 1 1 2。", "runtime"),
    ("correlator_output_path", "请提供 correlator 输出路径，例如 outputs/pion_twopt.npy。", "runtime"),
    ("resource_path", "请提供 QUDA resource_path，例如 .cache/quda。", "runtime"),
    ("cluster_launch", "请提供集群/运行假设，例如 local、mpi、slurm。", "runtime"),
    ("script_output_path", "请提供最终 Python 脚本输出路径。", "runtime"),
)

QUESTION_PRIORITY = {
    "start_from": 100,
    "source_timeslices": 95,
    "gauge_fixed": 90,
    "propagator_format": 86,
    "propagator_paths": 85,
    "fermion_action": 84,
    "mass": 82,
    "xi_0": 81,
    "nu": 80,
    "coeff_t": 79,
    "coeff_r": 78,
    "solver_tol": 77,
    "solver_maxiter": 76,
    "flow_steps": 83,
    "flow_epsilon": 83,
    "gauge_path": 63,
    "lattice_size": 58,
    "grid_size": 57,
    "resource_path": 56,
    "cluster_launch": 55,
    "correlator_output_path": 54,
    "script_output_path": 53,
}
QUESTION_PROMPTS = {field_name: (prompt, category) for field_name, prompt, category in QUESTION_ORDER}

DEFAULT_RESOURCE_PATH = ".cache/quda"
DEFAULT_CLUSTER_LAUNCH = "local"


def _field_priority(field_name: str, draft: Pion2ptTaskDraft) -> int:
    base = QUESTION_PRIORITY.get(field_name, 0)
    workflow = getattr(draft, "chosen_workflow_target", None) or draft.workflow_id
    if workflow == PION_2PT_PROPAGATOR_WORKFLOW_ID:
        if field_name in {"propagator_format", "propagator_paths"}:
            base += 20
        if field_name in {"resource_path", "cluster_launch", "script_output_path", "correlator_output_path"}:
            base += 12
        if field_name == "gauge_fixed":
            base += 6
    elif workflow == PROTON_2PT_PROPAGATOR_WORKFLOW_ID:
        if field_name in {"propagator_format", "propagator_paths", "source_timeslices"}:
            base += 22
        if field_name in {"resource_path", "cluster_launch", "script_output_path", "correlator_output_path"}:
            base += 12
        if field_name == "gauge_fixed":
            base += 8
    elif workflow == MESON_SPEC_PROPAGATOR_WORKFLOW_ID:
        if field_name in {"propagator_format", "propagator_paths", "source_timeslices"}:
            base += 22
        if field_name in {"resource_path", "cluster_launch", "script_output_path", "correlator_output_path"}:
            base += 12
        if field_name == "gauge_fixed":
            base += 8
    elif workflow == PION_PCAC_PROPAGATOR_WORKFLOW_ID:
        if field_name in {"propagator_format", "propagator_paths", "source_timeslices"}:
            base += 22
        if field_name in {"resource_path", "cluster_launch", "script_output_path", "correlator_output_path"}:
            base += 12
        if field_name == "gauge_fixed":
            base += 8
    elif workflow == PION_PCAC_WORKFLOW_ID:
        if field_name == "source_timeslices":
            base += 4
        if field_name == "mass":
            base += 3
    elif workflow == PION_DISPERSION_WORKFLOW_ID and field_name == "source_timeslices":
        base += 5
    elif workflow == MESON_SPEC_WORKFLOW_ID:
        if field_name == "gauge_fixed":
            base += 8
        if field_name == "source_timeslices":
            base -= 80
    elif workflow == PROTON_2PT_WORKFLOW_ID and field_name == "mass":
        base += 3
    elif workflow == RHO_VECTOR_PROPAGATOR_WORKFLOW_ID:
        if field_name in {"propagator_format", "propagator_paths", "source_timeslices"}:
            base += 22
        if field_name in {"resource_path", "cluster_launch", "script_output_path", "correlator_output_path"}:
            base += 12
        if field_name == "gauge_fixed":
            base += 8
    elif workflow == RHO_VECTOR_WORKFLOW_ID:
        if field_name == "source_timeslices":
            base += 4
        if field_name == "mass":
            base += 3
    elif workflow in {QUARK_PROPAGATOR_WORKFLOW_ID, QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID}:
        if field_name == "source_timeslices":
            base += 6
        if field_name in {"mass", "xi_0", "nu", "coeff_t", "coeff_r", "solver_tol", "solver_maxiter"}:
            base += 3
    elif workflow == WILSON_FLOW_WORKFLOW_ID:
        if field_name in {"flow_steps", "flow_epsilon"}:
            base += 16
        if field_name == "gauge_path":
            base += 8
    elif workflow in {APE_SMEAR_WORKFLOW_ID, HYP_SMEAR_WORKFLOW_ID, STOUT_SMEAR_WORKFLOW_ID} and field_name == "gauge_path":
        base += 8
    if field_name in {"resource_path", "cluster_launch"}:
        base += 2
    return base


def _record_unsupported(draft: Pion2ptTaskDraft, field_name: str, reason: str) -> None:
    if reason not in draft.unsupported_reasons:
        draft.unsupported_reasons.append(reason)
    draft.unsupported_fields[field_name] = reason


def _momentum_key(momentum: list[int]) -> tuple[int, int, int]:
    return tuple(int(item) for item in momentum)


def _apply_low_friction_defaults(draft: Pion2ptTaskDraft) -> None:
    if not draft.resource_path:
        draft.resource_path = DEFAULT_RESOURCE_PATH
        draft.field_sources["resource_path"] = "default"
    if not draft.cluster_launch:
        draft.cluster_launch = DEFAULT_CLUSTER_LAUNCH
        draft.field_sources["cluster_launch"] = "default"


def determine_missing_fields(draft: Pion2ptTaskDraft) -> list[str]:
    missing: list[str] = []
    draft.unsupported_reasons = []
    draft.unsupported_fields = {}
    _apply_low_friction_defaults(draft)
    workflow = getattr(draft, "chosen_workflow_target", None) or draft.workflow_id

    supported_action = "clover"
    supported_gauge_format = "chroma_qio"
    supported_output = "npy"
    supported_source = "wall"
    supported_sink = "local"
    supported_momentum = "zero"
    supported_gauge_fixed: bool | None = None
    supported_momenta = [[0, 0, 0]]
    supported_gamma_insertions: list[str] = []
    if workflow == PION_DISPERSION_WORKFLOW_ID:
        supported_source = "point"
        supported_sink = "local"
        supported_momentum = "explicit"
        supported_gauge_fixed = False
        supported_momenta = [list(item) for item in PION_DISPERSION_MOMENTA]
    elif workflow == PION_PCAC_WORKFLOW_ID:
        supported_source = "wall"
        supported_sink = "local"
        supported_momentum = "zero"
        supported_gauge_fixed = False
        supported_momenta = [[0, 0, 0]]
    elif workflow == PION_PCAC_PROPAGATOR_WORKFLOW_ID:
        supported_source = "wall"
        supported_sink = "local"
        supported_momentum = "zero"
        supported_gauge_fixed = False
        supported_momenta = [[0, 0, 0]]
    elif workflow == MESON_SPEC_WORKFLOW_ID:
        supported_source = "wall"
        supported_sink = "local"
        supported_momentum = "explicit"
        supported_gauge_fixed = False
        supported_momenta = [list(item) for item in MESON_SPEC_MOMENTA]
        supported_gamma_insertions = list(MESON_SPEC_GAMMA_INSERTIONS)
    elif workflow == MESON_SPEC_PROPAGATOR_WORKFLOW_ID:
        supported_source = "wall"
        supported_sink = "local"
        supported_momentum = "explicit"
        supported_gauge_fixed = False
        supported_momenta = [list(item) for item in MESON_SPEC_MOMENTA]
        supported_gamma_insertions = list(MESON_SPEC_GAMMA_INSERTIONS)
    elif workflow == PROTON_2PT_WORKFLOW_ID:
        supported_source = "wall"
        supported_sink = "local"
        supported_momentum = "zero"
        supported_gauge_fixed = False
        supported_momenta = [[0, 0, 0]]
    elif workflow == RHO_VECTOR_PROPAGATOR_WORKFLOW_ID:
        supported_source = "wall"
        supported_sink = "local"
        supported_momentum = "zero"
        supported_gauge_fixed = False
        supported_momenta = [[0, 0, 0]]
        supported_gamma_insertions = list(RHO_VECTOR_GAMMA_INSERTIONS)
    elif workflow == RHO_VECTOR_WORKFLOW_ID:
        supported_source = "wall"
        supported_sink = "local"
        supported_momentum = "zero"
        supported_gauge_fixed = False
        supported_momenta = [[0, 0, 0]]
        supported_gamma_insertions = list(RHO_VECTOR_GAMMA_INSERTIONS)
    elif workflow in {QUARK_PROPAGATOR_WORKFLOW_ID, QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID}:
        supported_source = "point"
        supported_sink = "propagator"
        supported_momentum = "none"
        supported_gauge_fixed = False
        supported_momenta = []
        supported_output = "hdf5"
    elif workflow == WILSON_FLOW_WORKFLOW_ID:
        supported_source = "none"
        supported_sink = "gauge"
        supported_momentum = "none"
        supported_gauge_fixed = False
        supported_momenta = []
        supported_output = "npy"
    elif workflow == STOUT_SMEAR_WORKFLOW_ID:
        supported_source = "none"
        supported_sink = "gauge"
        supported_momentum = "none"
        supported_gauge_fixed = False
        supported_momenta = []
        supported_output = "npy"
    elif workflow == APE_SMEAR_WORKFLOW_ID:
        supported_source = "none"
        supported_sink = "gauge"
        supported_momentum = "none"
        supported_gauge_fixed = False
        supported_momenta = []
        supported_output = "npy"
    elif workflow == HYP_SMEAR_WORKFLOW_ID:
        supported_source = "none"
        supported_sink = "gauge"
        supported_momentum = "none"
        supported_gauge_fixed = False
        supported_momenta = []
        supported_output = "npy"

    if workflow == PION_2PT_WORKFLOW_ID:
        if draft.task_type != "pion_2pt":
            missing.append("task_type")
        if draft.workflow_id != PION_2PT_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == PION_2PT_PROPAGATOR_WORKFLOW_ID:
        if draft.task_type != "pion_2pt":
            missing.append("task_type")
        if draft.workflow_id != PION_2PT_PROPAGATOR_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == PION_PCAC_WORKFLOW_ID:
        if draft.task_type != "pion_pcac":
            missing.append("task_type")
        if draft.workflow_id != PION_PCAC_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == PION_PCAC_PROPAGATOR_WORKFLOW_ID:
        if draft.task_type != "pion_pcac":
            missing.append("task_type")
        if draft.workflow_id != PION_PCAC_PROPAGATOR_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == PION_DISPERSION_WORKFLOW_ID:
        if draft.task_type != "pion_dispersion":
            missing.append("task_type")
        if draft.workflow_id != PION_DISPERSION_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == MESON_SPEC_WORKFLOW_ID:
        if draft.task_type != "meson_spec":
            missing.append("task_type")
        if draft.workflow_id != MESON_SPEC_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == MESON_SPEC_PROPAGATOR_WORKFLOW_ID:
        if draft.task_type != "meson_spec":
            missing.append("task_type")
        if draft.workflow_id != MESON_SPEC_PROPAGATOR_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == PROTON_2PT_WORKFLOW_ID:
        if draft.task_type != "proton_2pt":
            missing.append("task_type")
        if draft.workflow_id != PROTON_2PT_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == PROTON_2PT_PROPAGATOR_WORKFLOW_ID:
        if draft.task_type != "proton_2pt":
            missing.append("task_type")
        if draft.workflow_id != PROTON_2PT_PROPAGATOR_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == RHO_VECTOR_PROPAGATOR_WORKFLOW_ID:
        if draft.task_type != "rho_vector":
            missing.append("task_type")
        if draft.workflow_id != RHO_VECTOR_PROPAGATOR_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == RHO_VECTOR_WORKFLOW_ID:
        if draft.task_type != "rho_vector":
            missing.append("task_type")
        if draft.workflow_id != RHO_VECTOR_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == QUARK_PROPAGATOR_WORKFLOW_ID:
        if draft.task_type != "quark_propagator":
            missing.append("task_type")
        if draft.workflow_id != QUARK_PROPAGATOR_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID:
        if draft.task_type != "quark_propagator":
            missing.append("task_type")
        if draft.workflow_id != QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == WILSON_FLOW_WORKFLOW_ID:
        if draft.task_type != "wilson_flow":
            missing.append("task_type")
        if draft.workflow_id != WILSON_FLOW_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == STOUT_SMEAR_WORKFLOW_ID:
        if draft.task_type != "stout_smear":
            missing.append("task_type")
        if draft.workflow_id != STOUT_SMEAR_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == APE_SMEAR_WORKFLOW_ID:
        if draft.task_type != "ape_smear":
            missing.append("task_type")
        if draft.workflow_id != APE_SMEAR_WORKFLOW_ID:
            missing.append("workflow_id")
    elif workflow == HYP_SMEAR_WORKFLOW_ID:
        if draft.task_type != "hyp_smear":
            missing.append("task_type")
        if draft.workflow_id != HYP_SMEAR_WORKFLOW_ID:
            missing.append("workflow_id")

    if draft.start_from is None:
        missing.append("start_from")
    elif workflow == PION_2PT_PROPAGATOR_WORKFLOW_ID:
        if draft.start_from != "propagator":
            _record_unsupported(draft, "start_from", "Current propagator-entry pion family requires start_from=propagator.")
    elif workflow == PROTON_2PT_PROPAGATOR_WORKFLOW_ID:
        if draft.start_from != "propagator":
            _record_unsupported(draft, "start_from", "Current propagator-entry proton family requires start_from=propagator.")
    elif workflow == PION_PCAC_PROPAGATOR_WORKFLOW_ID:
        if draft.start_from != "propagator":
            _record_unsupported(draft, "start_from", "Current propagator-entry pion PCAC family requires start_from=propagator.")
    elif workflow == MESON_SPEC_PROPAGATOR_WORKFLOW_ID:
        if draft.start_from != "propagator":
            _record_unsupported(draft, "start_from", "Current propagator-entry meson-spectroscopy family requires start_from=propagator.")
    elif workflow == RHO_VECTOR_PROPAGATOR_WORKFLOW_ID:
        if draft.start_from != "propagator":
            _record_unsupported(draft, "start_from", "Current propagator-entry rho/vector family requires start_from=propagator.")
    elif workflow == STOUT_SMEAR_WORKFLOW_ID:
        if draft.start_from != "gauge":
            _record_unsupported(draft, "start_from", "Current stout-smear workflow only supports starting from a gauge configuration.")
    elif workflow == APE_SMEAR_WORKFLOW_ID:
        if draft.start_from != "gauge":
            _record_unsupported(draft, "start_from", "Current APE-smear workflow only supports starting from a gauge configuration.")
    elif workflow == HYP_SMEAR_WORKFLOW_ID:
        if draft.start_from != "gauge":
            _record_unsupported(draft, "start_from", "Current HYP-smear workflow only supports starting from a gauge configuration.")
    elif draft.start_from != "gauge":
        _record_unsupported(draft, "start_from", "First version only supports starting from a gauge configuration.")

    if draft.has_existing_propagators is None and draft.start_from is None:
        missing.append("has_existing_propagators")
    elif workflow not in {PION_2PT_PROPAGATOR_WORKFLOW_ID, PION_PCAC_PROPAGATOR_WORKFLOW_ID, MESON_SPEC_PROPAGATOR_WORKFLOW_ID, PROTON_2PT_PROPAGATOR_WORKFLOW_ID, RHO_VECTOR_PROPAGATOR_WORKFLOW_ID} and draft.has_existing_propagators:
        _record_unsupported(draft, "has_existing_propagators", "This workflow does not support starting from existing propagators.")
        if draft.propagator_format is None:
            missing.append("propagator_format")
        if not draft.propagator_paths:
            missing.append("propagator_paths")
    elif workflow == PION_2PT_PROPAGATOR_WORKFLOW_ID:
        if not draft.has_existing_propagators:
            _record_unsupported(draft, "has_existing_propagators", "Current propagator-entry pion family requires existing propagators.")
        if draft.propagator_format is None:
            missing.append("propagator_format")
        if not draft.propagator_paths:
            missing.append("propagator_paths")
    elif workflow == PROTON_2PT_PROPAGATOR_WORKFLOW_ID:
        if not draft.has_existing_propagators:
            _record_unsupported(draft, "has_existing_propagators", "Current propagator-entry proton family requires existing propagators.")
        if draft.propagator_format is None:
            missing.append("propagator_format")
        if not draft.propagator_paths:
            missing.append("propagator_paths")
    elif workflow == PION_PCAC_PROPAGATOR_WORKFLOW_ID:
        if not draft.has_existing_propagators:
            _record_unsupported(draft, "has_existing_propagators", "Current propagator-entry pion PCAC family requires existing propagators.")
        if draft.propagator_format is None:
            missing.append("propagator_format")
        if not draft.propagator_paths:
            missing.append("propagator_paths")
    elif workflow == MESON_SPEC_PROPAGATOR_WORKFLOW_ID:
        if not draft.has_existing_propagators:
            _record_unsupported(draft, "has_existing_propagators", "Current propagator-entry meson-spectroscopy family requires existing propagators.")
        if draft.propagator_format is None:
            missing.append("propagator_format")
        if not draft.propagator_paths:
            missing.append("propagator_paths")
    elif workflow == RHO_VECTOR_PROPAGATOR_WORKFLOW_ID:
        if not draft.has_existing_propagators:
            _record_unsupported(draft, "has_existing_propagators", "Current propagator-entry rho/vector family requires existing propagators.")
        if draft.propagator_format is None:
            missing.append("propagator_format")
        if not draft.propagator_paths:
            missing.append("propagator_paths")

    if workflow not in {PION_2PT_PROPAGATOR_WORKFLOW_ID, PION_PCAC_PROPAGATOR_WORKFLOW_ID, MESON_SPEC_PROPAGATOR_WORKFLOW_ID, PROTON_2PT_PROPAGATOR_WORKFLOW_ID, RHO_VECTOR_PROPAGATOR_WORKFLOW_ID} and draft.gauge_format is None:
        missing.append("gauge_format")
    elif workflow not in {PION_2PT_PROPAGATOR_WORKFLOW_ID, PION_PCAC_PROPAGATOR_WORKFLOW_ID, MESON_SPEC_PROPAGATOR_WORKFLOW_ID, PROTON_2PT_PROPAGATOR_WORKFLOW_ID, RHO_VECTOR_PROPAGATOR_WORKFLOW_ID} and draft.gauge_format != supported_gauge_format:
        _record_unsupported(draft, "gauge_format", "First version only supports Chroma/QIO gauge input.")

    if workflow not in {PION_2PT_PROPAGATOR_WORKFLOW_ID, PION_PCAC_PROPAGATOR_WORKFLOW_ID, MESON_SPEC_PROPAGATOR_WORKFLOW_ID, PROTON_2PT_PROPAGATOR_WORKFLOW_ID, RHO_VECTOR_PROPAGATOR_WORKFLOW_ID} and not draft.gauge_path:
        missing.append("gauge_path")
    if not draft.lattice_size:
        missing.append("lattice_size")
    if not draft.grid_size:
        missing.append("grid_size")
    elif workflow in {MESON_SPEC_WORKFLOW_ID, MESON_SPEC_PROPAGATOR_WORKFLOW_ID} and len(draft.grid_size) == 4 and draft.grid_size[3] != 1:
        _record_unsupported(
            draft,
            "grid_size",
            "Current meson-spectroscopy workflow is only grounded for GRID_SIZE[3] == 1 because the local upstream path stores the full source-timeslice sweep on one temporal rank.",
        )

    if workflow not in {
        PION_2PT_PROPAGATOR_WORKFLOW_ID,
        PION_PCAC_PROPAGATOR_WORKFLOW_ID,
        MESON_SPEC_PROPAGATOR_WORKFLOW_ID,
        PROTON_2PT_PROPAGATOR_WORKFLOW_ID,
        RHO_VECTOR_PROPAGATOR_WORKFLOW_ID,
        WILSON_FLOW_WORKFLOW_ID,
        APE_SMEAR_WORKFLOW_ID,
        HYP_SMEAR_WORKFLOW_ID,
        STOUT_SMEAR_WORKFLOW_ID,
    } and draft.fermion_action is None:
        missing.append("fermion_action")
    elif workflow not in {
        PION_2PT_PROPAGATOR_WORKFLOW_ID,
        PION_PCAC_PROPAGATOR_WORKFLOW_ID,
        MESON_SPEC_PROPAGATOR_WORKFLOW_ID,
        PROTON_2PT_PROPAGATOR_WORKFLOW_ID,
        RHO_VECTOR_PROPAGATOR_WORKFLOW_ID,
        WILSON_FLOW_WORKFLOW_ID,
        APE_SMEAR_WORKFLOW_ID,
        HYP_SMEAR_WORKFLOW_ID,
        STOUT_SMEAR_WORKFLOW_ID,
    } and draft.fermion_action != supported_action:
        _record_unsupported(draft, "fermion_action", "First version only supports Clover fermion action.")

    parameter_fields = ("mass", "xi_0", "nu", "coeff_t", "coeff_r", "solver_tol", "solver_maxiter")
    if workflow in {
        PION_2PT_PROPAGATOR_WORKFLOW_ID,
        PION_PCAC_PROPAGATOR_WORKFLOW_ID,
        MESON_SPEC_PROPAGATOR_WORKFLOW_ID,
        PROTON_2PT_PROPAGATOR_WORKFLOW_ID,
        RHO_VECTOR_PROPAGATOR_WORKFLOW_ID,
        WILSON_FLOW_WORKFLOW_ID,
        APE_SMEAR_WORKFLOW_ID,
        HYP_SMEAR_WORKFLOW_ID,
        STOUT_SMEAR_WORKFLOW_ID,
    }:
        parameter_fields = ()
    for field_name in parameter_fields:
        if getattr(draft, field_name) is None:
            missing.append(field_name)

    propagator_family_supported_sources = {"wall", "point"}
    if draft.source_type is None:
        missing.append("source_type")
    elif workflow == PION_2PT_PROPAGATOR_WORKFLOW_ID and draft.source_type not in propagator_family_supported_sources:
        _record_unsupported(
            draft,
            "source_type",
            "Current propagator-entry pion family only supports source_type in {'wall', 'point'} based on local PyQUDA source conventions and IO tests.",
        )
    elif workflow == PROTON_2PT_PROPAGATOR_WORKFLOW_ID and draft.source_type != "wall":
        _record_unsupported(
            draft,
            "source_type",
            "Current propagator-entry proton family only supports source_type='wall' because the grounded local proton contraction path is traced to the wall-source example.",
        )
    elif workflow == PION_PCAC_PROPAGATOR_WORKFLOW_ID and draft.source_type != "wall":
        _record_unsupported(
            draft,
            "source_type",
            "Current propagator-entry pion PCAC family only supports source_type='wall' because the grounded local PCAC contraction path is traced to the wall-source upstream example.",
        )
    elif workflow == MESON_SPEC_PROPAGATOR_WORKFLOW_ID and draft.source_type != "wall":
        _record_unsupported(
            draft,
            "source_type",
            "Current propagator-entry meson-spectroscopy family only supports source_type='wall' because the grounded contraction path is traced to the wall-source mesonspec test.",
        )
    elif workflow == RHO_VECTOR_PROPAGATOR_WORKFLOW_ID and draft.source_type != "wall":
        _record_unsupported(
            draft,
            "source_type",
            "Current propagator-entry rho/vector family only supports source_type='wall' because the grounded contraction path is traced to the wall-source mesonspec test.",
        )
    elif draft.source_type != supported_source:
        if workflow == PION_DISPERSION_WORKFLOW_ID:
            _record_unsupported(draft, "source_type", "Current pion-dispersion workflow only supports point source at the spatial origin.")
        elif workflow == PION_PCAC_WORKFLOW_ID:
            _record_unsupported(draft, "source_type", "Current pion PCAC workflow only supports wall source.")
        elif workflow == PROTON_2PT_WORKFLOW_ID:
            _record_unsupported(draft, "source_type", "Current proton workflow only supports wall source.")
        elif workflow == RHO_VECTOR_WORKFLOW_ID:
            _record_unsupported(draft, "source_type", "Current rho/vector workflow only supports wall source.")
        elif workflow == QUARK_PROPAGATOR_WORKFLOW_ID:
            _record_unsupported(draft, "source_type", "Current quark-propagator workflow only supports point source at the fixed spatial origin [0, 0, 0].")
        elif workflow == QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID:
            _record_unsupported(draft, "source_type", "Current gaussian-shell quark-propagator workflow only supports a point-source seed at the fixed spatial origin [0, 0, 0] before gaussianSmear.")
        elif workflow == STOUT_SMEAR_WORKFLOW_ID:
            _record_unsupported(draft, "source_type", "Current stout-smear workflow does not use source_type; leave it unspecified.")
        elif workflow == APE_SMEAR_WORKFLOW_ID:
            _record_unsupported(draft, "source_type", "Current APE-smear workflow does not use source_type; leave it unspecified.")
        else:
            _record_unsupported(draft, "source_type", "First version only supports wall source.")

    if draft.sink_type is None:
        missing.append("sink_type")
    elif draft.sink_type != supported_sink:
        if workflow in {QUARK_PROPAGATOR_WORKFLOW_ID, QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID}:
            _record_unsupported(draft, "sink_type", "Current quark-propagator workflow writes the propagator directly and requires sink_type='propagator'.")
        elif workflow == STOUT_SMEAR_WORKFLOW_ID:
            _record_unsupported(draft, "sink_type", "Current stout-smear workflow writes a smeared gauge artifact and requires sink_type='gauge'.")
        elif workflow == APE_SMEAR_WORKFLOW_ID:
            _record_unsupported(draft, "sink_type", "Current APE-smear workflow writes a smeared gauge artifact and requires sink_type='gauge'.")
        else:
            _record_unsupported(draft, "sink_type", "First version only supports local sink.")

    if workflow in {MESON_SPEC_WORKFLOW_ID, MESON_SPEC_PROPAGATOR_WORKFLOW_ID, RHO_VECTOR_WORKFLOW_ID, RHO_VECTOR_PROPAGATOR_WORKFLOW_ID}:
        if draft.gamma_insertions and draft.gamma_insertions != supported_gamma_insertions:
            expected_message = (
                "Current rho/vector workflow only supports gamma_insertions == ['gamma1_gamma1', 'gamma2_gamma2', 'gamma3_gamma3']."
                if workflow in {RHO_VECTOR_WORKFLOW_ID, RHO_VECTOR_PROPAGATOR_WORKFLOW_ID}
                else "Meson-spectroscopy workflow only supports gamma_insertions == ['gamma5_gamma5', 'gamma4gamma5_gamma4gamma5']."
            )
            _record_unsupported(
                draft,
                "gamma_insertions",
                expected_message,
            )
        elif not draft.gamma_insertions:
            draft.gamma_insertions = list(supported_gamma_insertions)
            draft.field_sources.setdefault("gamma_insertions", "fixed")
            draft.fixed_fields.setdefault("gamma_insertions", list(supported_gamma_insertions))

    if draft.momentum_projection is None:
        missing.append("momentum_projection")
    elif draft.momentum_projection != supported_momentum:
        if workflow == PION_DISPERSION_WORKFLOW_ID:
            _record_unsupported(draft, "momentum_projection", "Current pion-dispersion workflow only supports the fixed explicit momentum list from the local example.")
        elif workflow in {MESON_SPEC_WORKFLOW_ID, MESON_SPEC_PROPAGATOR_WORKFLOW_ID}:
            _record_unsupported(
                draft,
                "momentum_projection",
                "Current meson-spectroscopy workflow only supports the grounded explicit momentum family from tests/test_mesonspec.py.",
            )
        elif workflow == RHO_VECTOR_WORKFLOW_ID:
            _record_unsupported(draft, "momentum_projection", "Current rho/vector workflow only supports zero-momentum rho correlators.")
        elif workflow == RHO_VECTOR_PROPAGATOR_WORKFLOW_ID:
            _record_unsupported(draft, "momentum_projection", "Current propagator-entry rho/vector workflow only supports zero-momentum rho correlators.")
        elif workflow == PROTON_2PT_WORKFLOW_ID:
            _record_unsupported(draft, "momentum_projection", "Current proton workflow only supports zero-momentum proton 2pt.")
        elif workflow == PROTON_2PT_PROPAGATOR_WORKFLOW_ID:
            _record_unsupported(draft, "momentum_projection", "Current propagator-entry proton workflow only supports zero-momentum proton 2pt.")
        elif workflow == PION_PCAC_PROPAGATOR_WORKFLOW_ID:
            _record_unsupported(draft, "momentum_projection", "Current propagator-entry pion PCAC workflow only supports zero-momentum pion and pionA4 contractions.")
        elif workflow == PION_PCAC_WORKFLOW_ID:
            _record_unsupported(draft, "momentum_projection", "Current pion PCAC workflow only supports zero-momentum pion and pionA4 contractions.")
        elif workflow in {QUARK_PROPAGATOR_WORKFLOW_ID, QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID}:
            _record_unsupported(draft, "momentum_projection", "Current quark-propagator workflow does not perform momentum projection and requires momentum_projection='none'.")
        elif workflow == STOUT_SMEAR_WORKFLOW_ID:
            _record_unsupported(draft, "momentum_projection", "Current stout-smear workflow does not perform momentum projection and requires momentum_projection='none'.")
        elif workflow == APE_SMEAR_WORKFLOW_ID:
            _record_unsupported(draft, "momentum_projection", "Current APE-smear workflow does not perform momentum projection and requires momentum_projection='none'.")
        elif workflow == HYP_SMEAR_WORKFLOW_ID:
            _record_unsupported(draft, "momentum_projection", "Current HYP-smear workflow does not perform momentum projection and requires momentum_projection='none'.")
        else:
            _record_unsupported(draft, "momentum_projection", "First version only supports zero-momentum pion 2pt.")

    if workflow == WILSON_FLOW_WORKFLOW_ID:
        if draft.source_type not in (None, "none"):
            _record_unsupported(draft, "source_type", "Current Wilson-flow workflow does not use source_type; leave it unspecified.")
    elif workflow == APE_SMEAR_WORKFLOW_ID:
        if draft.momenta not in ([], None):
            _record_unsupported(draft, "momenta", "Current APE-smear workflow requires momenta == [].")
    elif workflow == HYP_SMEAR_WORKFLOW_ID:
        if draft.momenta not in ([], None):
            _record_unsupported(draft, "momenta", "Current HYP-smear workflow requires momenta == [].")
    elif workflow == STOUT_SMEAR_WORKFLOW_ID:
        if draft.momenta not in ([], None):
            _record_unsupported(draft, "momenta", "Current stout-smear workflow requires momenta == [].")
    elif workflow in {QUARK_PROPAGATOR_WORKFLOW_ID, QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID}:
        if draft.momenta not in ([], None):
            _record_unsupported(draft, "momenta", "Current quark-propagator workflow requires momenta == [].")
    elif not draft.momenta:
        missing.append("momenta")
    elif draft.momentum_projection == supported_momentum:
        if workflow == PION_DISPERSION_WORKFLOW_ID:
            supported_set = {_momentum_key(item) for item in supported_momenta}
            invalid_momenta = [momentum for momentum in draft.momenta if _momentum_key(momentum) not in supported_set]
            if invalid_momenta:
                _record_unsupported(
                    draft,
                    "momenta",
                    "Pion-dispersion workflow only supports momentum vectors drawn from the locally grounded 9-momentum family in examples/5_Pion_Dispersion.py.",
                )
        elif workflow in {MESON_SPEC_WORKFLOW_ID, MESON_SPEC_PROPAGATOR_WORKFLOW_ID}:
            supported_set = {_momentum_key(item) for item in supported_momenta}
            invalid_momenta = [momentum for momentum in draft.momenta if _momentum_key(momentum) not in supported_set]
            if invalid_momenta:
                _record_unsupported(
                    draft,
                    "momenta",
                    "Meson-spectroscopy workflow only supports momentum vectors drawn from the locally grounded |p|^2<=9 family in tests/test_mesonspec.py.",
                )
        elif draft.momenta != supported_momenta:
            if workflow in {PROTON_2PT_WORKFLOW_ID, PROTON_2PT_PROPAGATOR_WORKFLOW_ID}:
                _record_unsupported(draft, "momenta", "Proton workflow requires momenta == [[0, 0, 0]].")
            elif workflow in {RHO_VECTOR_WORKFLOW_ID, RHO_VECTOR_PROPAGATOR_WORKFLOW_ID}:
                _record_unsupported(draft, "momenta", "Rho/vector workflow requires momenta == [[0, 0, 0]].")
            else:
                _record_unsupported(draft, "momenta", "Zero-momentum workflow requires momenta == [[0, 0, 0]].")

    if workflow == WILSON_FLOW_WORKFLOW_ID:
        if draft.flow_steps is None:
            missing.append("flow_steps")
        if draft.flow_epsilon is None:
            missing.append("flow_epsilon")
    elif workflow == APE_SMEAR_WORKFLOW_ID:
        pass
    elif workflow == HYP_SMEAR_WORKFLOW_ID:
        pass
    elif workflow == STOUT_SMEAR_WORKFLOW_ID:
        if draft.stout_smear_steps not in (None, 1):
            _record_unsupported(draft, "stout_smear_steps", "Current stout-smear workflow is fixed to stout_smear_steps=1 from the local test_smear path.")
        if draft.stout_smear_rho not in (None, 0.241):
            _record_unsupported(draft, "stout_smear_rho", "Current stout-smear workflow is fixed to stout_smear_rho=0.241 from the local test_smear path.")
        if draft.stout_smear_ndim not in (None, 3):
            _record_unsupported(draft, "stout_smear_ndim", "Current stout-smear workflow is fixed to stout_smear_ndim=3 from the local test_smear path.")
    elif workflow not in {
        PION_2PT_PROPAGATOR_WORKFLOW_ID,
        PION_PCAC_PROPAGATOR_WORKFLOW_ID,
        MESON_SPEC_WORKFLOW_ID,
        MESON_SPEC_PROPAGATOR_WORKFLOW_ID,
        PROTON_2PT_PROPAGATOR_WORKFLOW_ID,
        RHO_VECTOR_PROPAGATOR_WORKFLOW_ID,
        APE_SMEAR_WORKFLOW_ID,
        HYP_SMEAR_WORKFLOW_ID,
        STOUT_SMEAR_WORKFLOW_ID,
    } and not draft.source_timeslices:
        missing.append("source_timeslices")
    if workflow == PION_PCAC_PROPAGATOR_WORKFLOW_ID:
        if not draft.source_timeslices:
            missing.append("source_timeslices")
        elif draft.propagator_paths and len(draft.source_timeslices) != len(draft.propagator_paths):
            _record_unsupported(
                draft,
                "source_timeslices",
                "Current propagator-entry pion PCAC workflow requires len(source_timeslices) == len(propagator_paths).",
            )
    if workflow == PROTON_2PT_PROPAGATOR_WORKFLOW_ID:
        if not draft.source_timeslices:
            missing.append("source_timeslices")
        elif draft.propagator_paths and len(draft.source_timeslices) != len(draft.propagator_paths):
            _record_unsupported(
                draft,
                "source_timeslices",
                "Current propagator-entry proton workflow requires len(source_timeslices) == len(propagator_paths).",
            )
    if workflow == RHO_VECTOR_PROPAGATOR_WORKFLOW_ID:
        if not draft.source_timeslices:
            missing.append("source_timeslices")
        elif draft.propagator_paths and len(draft.source_timeslices) != len(draft.propagator_paths):
            _record_unsupported(
                draft,
                "source_timeslices",
                "Current propagator-entry rho/vector workflow requires len(source_timeslices) == len(propagator_paths).",
            )
    if workflow == MESON_SPEC_PROPAGATOR_WORKFLOW_ID:
        if not draft.source_timeslices:
            missing.append("source_timeslices")
        elif draft.propagator_paths and len(draft.source_timeslices) != len(draft.propagator_paths):
            _record_unsupported(
                draft,
                "source_timeslices",
                "Current propagator-entry meson-spectroscopy workflow requires len(source_timeslices) == len(propagator_paths).",
            )
    if workflow == PION_2PT_PROPAGATOR_WORKFLOW_ID:
        if draft.gauge_fixed is None:
            missing.append("gauge_fixed")
    elif workflow == PION_PCAC_PROPAGATOR_WORKFLOW_ID:
        if draft.gauge_fixed is None:
            missing.append("gauge_fixed")
        elif draft.gauge_fixed is not False:
            _record_unsupported(
                draft,
                "gauge_fixed",
                "Current propagator-entry pion PCAC workflow is only grounded for gauge_fixed=False to stay aligned with the local wall-source PCAC path.",
            )
    elif workflow == MESON_SPEC_PROPAGATOR_WORKFLOW_ID:
        if draft.gauge_fixed is None:
            missing.append("gauge_fixed")
        elif draft.gauge_fixed is not False:
            _record_unsupported(
                draft,
                "gauge_fixed",
                "Current propagator-entry meson-spectroscopy workflow is only grounded for gauge_fixed=false to stay aligned with the local mesonspec path.",
            )
    elif workflow == PROTON_2PT_PROPAGATOR_WORKFLOW_ID:
        if draft.gauge_fixed is None:
            missing.append("gauge_fixed")
        elif draft.gauge_fixed is not False:
            _record_unsupported(
                draft,
                "gauge_fixed",
                "Current propagator-entry proton workflow is only grounded for gauge_fixed=false to stay aligned with the local wall-source proton path.",
            )
    elif workflow == RHO_VECTOR_PROPAGATOR_WORKFLOW_ID:
        if draft.gauge_fixed is None:
            missing.append("gauge_fixed")
        elif draft.gauge_fixed is not False:
            _record_unsupported(
                draft,
                "gauge_fixed",
                "Current propagator-entry rho/vector workflow is only grounded for gauge_fixed=false to stay aligned with the local wall-source mesonspec path.",
            )
    elif supported_gauge_fixed is None and draft.gauge_fixed is None:
        missing.append("gauge_fixed")
    elif supported_gauge_fixed is not None and draft.gauge_fixed not in (supported_gauge_fixed, None):
        if workflow == PROTON_2PT_WORKFLOW_ID:
            _record_unsupported(draft, "gauge_fixed", "Current proton workflow does not include a gauge-fixing step.")
        elif workflow == RHO_VECTOR_WORKFLOW_ID:
            _record_unsupported(draft, "gauge_fixed", "Current rho/vector workflow does not include a gauge-fixing step.")
        elif workflow == PION_PCAC_WORKFLOW_ID:
            _record_unsupported(draft, "gauge_fixed", "Current pion PCAC workflow does not include a gauge-fixing step.")
        elif workflow == APE_SMEAR_WORKFLOW_ID:
            _record_unsupported(draft, "gauge_fixed", "Current APE-smear workflow does not include a gauge-fixing step.")
        elif workflow == HYP_SMEAR_WORKFLOW_ID:
            _record_unsupported(draft, "gauge_fixed", "Current HYP-smear workflow does not include a gauge-fixing step.")
        elif workflow == STOUT_SMEAR_WORKFLOW_ID:
            _record_unsupported(draft, "gauge_fixed", "Current stout-smear workflow does not include a gauge-fixing step.")
        else:
            _record_unsupported(draft, "gauge_fixed", "Current pion-dispersion workflow does not include a gauge-fixing step.")

    if draft.correlator_output_format is None:
        missing.append("correlator_output_format")
    elif draft.correlator_output_format != supported_output:
        if workflow in {QUARK_PROPAGATOR_WORKFLOW_ID, QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID}:
            _record_unsupported(draft, "correlator_output_format", "Current quark-propagator workflow only supports HDF5 propagator output.")
        else:
            _record_unsupported(draft, "correlator_output_format", "First version only supports .npy correlator output.")

    if not draft.correlator_output_path:
        missing.append("correlator_output_path")
    if not draft.script_output_path:
        missing.append("script_output_path")

    if draft.script_style is None:
        missing.append("script_style")
    elif draft.script_style != "complete":
        _record_unsupported(draft, "script_style", "This workflow only supports complete mode for runnable output.")

    draft.missing_fields = missing
    return missing


def build_questions(
    draft: Pion2ptTaskDraft,
    max_questions: int,
    preferred_fields: list[str] | None = None,
) -> list[ClarifyingQuestion]:
    missing = set(determine_missing_fields(draft))
    questions: list[ClarifyingQuestion] = []
    asked_fields = set(draft.clarified_fields) | set(draft.user_confirmed_fields) | {
        field_name for field_name, source in draft.field_sources.items() if source in {"fixed", "parsed", "default", "inherited"}
    }
    candidate_fields = [field_name for field_name in missing if field_name not in asked_fields and field_name in QUESTION_PROMPTS]
    candidate_fields.sort(key=lambda field_name: (-_field_priority(field_name, draft), field_name))
    preferred_order = []
    if preferred_fields:
        candidate_field_set = set(candidate_fields)
        preferred_order = [field_name for field_name in preferred_fields if field_name in candidate_field_set]
    if preferred_order:
        candidate_fields = preferred_order + [field_name for field_name in candidate_fields if field_name not in set(preferred_order)]

    selected_fields: set[str] = set()
    candidate_field_set = set(candidate_fields)
    effective_limit = max_questions

    def _append(field_name: str) -> None:
        if field_name in selected_fields or field_name not in QUESTION_PROMPTS:
            return
        prompt, category = QUESTION_PROMPTS[field_name]
        questions.append(ClarifyingQuestion(field_name=field_name, prompt=prompt, category=category, scope="task"))
        selected_fields.add(field_name)

    for field_name in candidate_fields:
        if len(questions) >= effective_limit:
            break
        if field_name in selected_fields:
            continue
        group_definition = FIELD_TO_GROUP.get(field_name)
        if group_definition is not None:
            remaining_group_fields = [
                grouped_field
                for grouped_field in group_definition.fields
                if grouped_field in candidate_field_set and grouped_field not in selected_fields
            ]
            remaining_slots = effective_limit - len(questions)
            if len(remaining_group_fields) == len(group_definition.fields):
                if remaining_slots >= len(remaining_group_fields):
                    for grouped_field in remaining_group_fields:
                        _append(grouped_field)
                    continue
                # If the batch is otherwise dominated by this stable group, expand once to keep it intact.
                if not questions and remaining_slots >= (len(remaining_group_fields) + 1) // 2:
                    effective_limit = len(remaining_group_fields)
                    for grouped_field in remaining_group_fields:
                        _append(grouped_field)
                    continue
        _append(field_name)
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
    draft.clarified_fields[field_name] = value
    if field_name == "start_from":
        draft.start_from = value.lower()
        draft.has_existing_propagators = value.lower() == "propagator"
        draft.field_sources["has_existing_propagators"] = "clarified"
        draft.clarified_fields["start_from"] = draft.start_from
        draft.clarified_fields["has_existing_propagators"] = draft.has_existing_propagators
    elif field_name == "has_existing_propagators":
        parsed = _parse_bool(value)
        if parsed is not None:
            draft.has_existing_propagators = parsed
            draft.clarified_fields["has_existing_propagators"] = parsed
            if parsed:
                draft.start_from = "propagator"
                draft.field_sources["start_from"] = "clarified"
                draft.clarified_fields["start_from"] = "propagator"
            elif draft.start_from is None:
                draft.start_from = "gauge"
                draft.field_sources["start_from"] = "clarified"
                draft.clarified_fields["start_from"] = "gauge"
    elif field_name == "gauge_format":
        draft.gauge_format = value.lower()
        draft.clarified_fields["gauge_format"] = draft.gauge_format
    elif field_name == "gauge_path":
        draft.gauge_path = value
        draft.clarified_fields["gauge_path"] = draft.gauge_path
    elif field_name == "propagator_format":
        draft.propagator_format = value.lower()
        draft.clarified_fields["propagator_format"] = draft.propagator_format
    elif field_name == "propagator_paths":
        draft.propagator_paths = _parse_path_list(value)
        draft.clarified_fields["propagator_paths"] = list(draft.propagator_paths)
    elif field_name == "lattice_size":
        draft.lattice_size = _parse_int_list(value)
        draft.clarified_fields["lattice_size"] = list(draft.lattice_size)
    elif field_name == "grid_size":
        draft.grid_size = _parse_int_list(value)
        draft.clarified_fields["grid_size"] = list(draft.grid_size)
    elif field_name == "fermion_action":
        draft.fermion_action = value.lower()
        draft.clarified_fields["fermion_action"] = draft.fermion_action
    elif field_name in {"mass", "xi_0", "nu", "coeff_t", "coeff_r", "solver_tol"}:
        setattr(draft, field_name, float(value))
        draft.clarified_fields[field_name] = getattr(draft, field_name)
    elif field_name == "solver_maxiter":
        draft.solver_maxiter = int(value)
        draft.clarified_fields["solver_maxiter"] = draft.solver_maxiter
    elif field_name == "flow_steps":
        draft.flow_steps = int(value)
        draft.clarified_fields["flow_steps"] = draft.flow_steps
    elif field_name == "flow_epsilon":
        draft.flow_epsilon = float(value)
        draft.clarified_fields["flow_epsilon"] = draft.flow_epsilon
    elif field_name == "source_type":
        draft.source_type = value.lower()
        draft.clarified_fields["source_type"] = draft.source_type
    elif field_name == "sink_type":
        draft.sink_type = value.lower()
        draft.clarified_fields["sink_type"] = draft.sink_type
    elif field_name == "momentum_projection":
        draft.momentum_projection = value.lower()
        draft.clarified_fields["momentum_projection"] = draft.momentum_projection
        if draft.momentum_projection == "zero":
            draft.momenta = [[0, 0, 0]]
            draft.field_sources["momenta"] = "fixed"
            draft.fixed_fields["momenta"] = [[0, 0, 0]]
        elif draft.momentum_projection == "none":
            draft.momenta = []
            draft.field_sources["momenta"] = "fixed"
            draft.fixed_fields["momenta"] = []
        elif draft.momentum_projection == "explicit" and (
            getattr(draft, "chosen_workflow_target", None) == PION_DISPERSION_WORKFLOW_ID or draft.workflow_id == PION_DISPERSION_WORKFLOW_ID
        ):
            draft.momenta = [list(item) for item in PION_DISPERSION_MOMENTA]
            draft.field_sources["momenta"] = "fixed"
            draft.fixed_fields["momenta"] = [list(item) for item in PION_DISPERSION_MOMENTA]
        elif draft.momentum_projection == "explicit" and (
            getattr(draft, "chosen_workflow_target", None) == MESON_SPEC_WORKFLOW_ID or draft.workflow_id == MESON_SPEC_WORKFLOW_ID
        ):
            draft.momenta = [list(item) for item in MESON_SPEC_MOMENTA]
            draft.field_sources["momenta"] = "fixed"
            draft.fixed_fields["momenta"] = [list(item) for item in MESON_SPEC_MOMENTA]
    elif field_name == "source_timeslices":
        draft.source_timeslices = _parse_int_list(value)
        draft.clarified_fields["source_timeslices"] = list(draft.source_timeslices)
    elif field_name == "gauge_fixed":
        parsed = _parse_bool(value)
        if parsed is not None:
            draft.gauge_fixed = parsed
            draft.clarified_fields["gauge_fixed"] = parsed
    elif field_name == "correlator_output_format":
        normalized = value.lower()
        if normalized == "h5":
            normalized = "hdf5"
        draft.correlator_output_format = normalized
        draft.clarified_fields["correlator_output_format"] = draft.correlator_output_format
    elif field_name == "correlator_output_path":
        draft.correlator_output_path = value
        draft.clarified_fields["correlator_output_path"] = draft.correlator_output_path
    elif field_name == "resource_path":
        draft.resource_path = value
        draft.clarified_fields["resource_path"] = draft.resource_path
    elif field_name == "cluster_launch":
        draft.cluster_launch = value
        draft.clarified_fields["cluster_launch"] = draft.cluster_launch
    elif field_name == "script_output_path":
        draft.script_output_path = value
        draft.clarified_fields["script_output_path"] = draft.script_output_path
    elif field_name == "script_style":
        draft.script_style = value.lower()
        draft.clarified_fields["script_style"] = draft.script_style
    determine_missing_fields(draft)
