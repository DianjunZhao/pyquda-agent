"""Map confirmed physics targets onto supported implementation workflows."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field

from pyquda_agent.intent.interpreter import APE_SMEAR_TARGET_ID
from pyquda_agent.intent.interpreter import HYP_SMEAR_TARGET_ID
from pyquda_agent.intent.interpreter import MESON_SPEC_TARGET_ID
from pyquda_agent.intent.interpreter import NEUTRON_TARGET_ID
from pyquda_agent.intent.interpreter import PION_PCAC_TARGET_ID
from pyquda_agent.intent.interpreter import PION_DISPERSION_TARGET_ID
from pyquda_agent.intent.interpreter import PION_TARGET_ID
from pyquda_agent.intent.interpreter import PROTON_TARGET_ID
from pyquda_agent.intent.interpreter import QUARK_PROPAGATOR_TARGET_ID
from pyquda_agent.intent.interpreter import RHO_TARGET_ID
from pyquda_agent.intent.interpreter import STOUT_SMEAR_TARGET_ID
from pyquda_agent.intent.interpreter import WILSON_FLOW_TARGET_ID
from pyquda_agent.intent.schema import PhysicsTargetArtifact
from pyquda_agent.retrieval.physics_citations import load_physics_citations
from pyquda_agent.retrieval.repo_scan import PINNED_APE_SMEAR_PYQUDA_FILES
from pyquda_agent.retrieval.repo_scan import PINNED_HYP_SMEAR_PYQUDA_FILES
from pyquda_agent.retrieval.repo_scan import PINNED_MESON_SPEC_PYQUDA_FILES
from pyquda_agent.retrieval.repo_scan import PINNED_MESON_SPEC_PROPAGATOR_PYQUDA_FILES
from pyquda_agent.retrieval.repo_scan import PINNED_PION_PCAC_PYQUDA_FILES
from pyquda_agent.retrieval.repo_scan import PINNED_PION_PCAC_PROPAGATOR_PYQUDA_FILES
from pyquda_agent.retrieval.repo_scan import PINNED_PION_DISPERSION_PYQUDA_FILES
from pyquda_agent.retrieval.repo_scan import PINNED_PION_2PT_PYQUDA_FILES
from pyquda_agent.retrieval.repo_scan import PINNED_PROTON_2PT_PROPAGATOR_PYQUDA_FILES
from pyquda_agent.retrieval.repo_scan import PINNED_PROTON_2PT_PYQUDA_FILES
from pyquda_agent.retrieval.repo_scan import PINNED_GAUSSIAN_SHELL_QUARK_PROPAGATOR_PYQUDA_FILES
from pyquda_agent.retrieval.repo_scan import PINNED_QUARK_PROPAGATOR_PYQUDA_FILES
from pyquda_agent.retrieval.repo_scan import PINNED_RHO_VECTOR_PROPAGATOR_PYQUDA_FILES
from pyquda_agent.retrieval.repo_scan import PINNED_RHO_VECTOR_PYQUDA_FILES
from pyquda_agent.retrieval.repo_scan import PINNED_STOUT_SMEAR_PYQUDA_FILES
from pyquda_agent.retrieval.repo_scan import PINNED_WILSON_FLOW_PYQUDA_FILES
from pyquda_agent.tasks.schema import Pion2ptTaskDraft


PION_2PT_WORKFLOW_ID = "pion_2pt_chroma_wall_local_zero_momentum_npy_v1"
PION_2PT_PROPAGATOR_WORKFLOW_ID = "pion_2pt_existing_propagator_local_zero_momentum_npy_v1"
PION_2PT_FIXED_FIELDS = {
    "task_type": "pion_2pt",
    "workflow_id": PION_2PT_WORKFLOW_ID,
    "start_from": "gauge",
    "has_existing_propagators": False,
    "gauge_format": "chroma_qio",
    "fermion_action": "clover",
    "source_type": "wall",
    "sink_type": "local",
    "momentum_projection": "zero",
    "momenta": [[0, 0, 0]],
    "correlator_output_format": "npy",
    "script_style": "complete",
}
PION_2PT_PROPAGATOR_FIXED_FIELDS = {
    "task_type": "pion_2pt",
    "workflow_id": PION_2PT_PROPAGATOR_WORKFLOW_ID,
    "start_from": "propagator",
    "has_existing_propagators": True,
    "sink_type": "local",
    "momentum_projection": "zero",
    "momenta": [[0, 0, 0]],
    "correlator_output_format": "npy",
    "script_style": "complete",
}
PION_DISPERSION_MOMENTA = [[0, 0, 0], [0, 0, 1], [0, 1, 1], [1, 1, 1], [0, 0, 2], [0, 1, 2], [1, 1, 2], [0, 2, 2], [1, 2, 2]]
PION_DISPERSION_WORKFLOW_ID = "pion_dispersion_chroma_point_momentum_npy_v1"
PION_DISPERSION_FIXED_FIELDS = {
    "task_type": "pion_dispersion",
    "workflow_id": PION_DISPERSION_WORKFLOW_ID,
    "start_from": "gauge",
    "has_existing_propagators": False,
    "gauge_format": "chroma_qio",
    "fermion_action": "clover",
    "source_type": "point",
    "sink_type": "local",
    "momentum_projection": "explicit",
    "momenta": [list(item) for item in PION_DISPERSION_MOMENTA],
    "gauge_fixed": False,
    "correlator_output_format": "npy",
    "script_style": "complete",
}
PION_PCAC_WORKFLOW_ID = "pion_pcac_chroma_wall_local_zero_momentum_npy_v1"
PION_PCAC_PROPAGATOR_WORKFLOW_ID = "pion_pcac_existing_propagator_local_zero_momentum_npy_v1"
PION_PCAC_FIXED_FIELDS = {
    "task_type": "pion_pcac",
    "workflow_id": PION_PCAC_WORKFLOW_ID,
    "start_from": "gauge",
    "has_existing_propagators": False,
    "gauge_format": "chroma_qio",
    "fermion_action": "clover",
    "multigrid_blocks": [[6, 6, 6, 4], [4, 4, 4, 9]],
    "stout_smear_steps": 1,
    "stout_smear_rho": 0.125,
    "stout_smear_ndim": 4,
    "source_type": "wall",
    "sink_type": "local",
    "momentum_projection": "zero",
    "momenta": [[0, 0, 0]],
    "gauge_fixed": False,
    "correlator_output_format": "npy",
    "script_style": "complete",
}
PION_PCAC_PROPAGATOR_FIXED_FIELDS = {
    "task_type": "pion_pcac",
    "workflow_id": PION_PCAC_PROPAGATOR_WORKFLOW_ID,
    "start_from": "propagator",
    "has_existing_propagators": True,
    "source_type": "wall",
    "sink_type": "local",
    "momentum_projection": "zero",
    "momenta": [[0, 0, 0]],
    "gauge_fixed": False,
    "correlator_output_format": "npy",
    "script_style": "complete",
}
MESON_SPEC_WORKFLOW_ID = "meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1"
MESON_SPEC_PROPAGATOR_WORKFLOW_ID = "meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1"
PROTON_2PT_WORKFLOW_ID = "proton_2pt_chroma_wall_local_zero_momentum_npy_v1"
PROTON_2PT_PROPAGATOR_WORKFLOW_ID = "proton_2pt_existing_propagator_local_zero_momentum_npy_v1"
QUARK_PROPAGATOR_WORKFLOW_ID = "quark_propagator_chroma_point_hdf5_v1"
QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID = "quark_propagator_gaussian_shell_chroma_hdf5_v1"
RHO_VECTOR_WORKFLOW_ID = "rho_vector_chroma_wall_local_zero_momentum_npy_v1"
RHO_VECTOR_PROPAGATOR_WORKFLOW_ID = "rho_vector_existing_propagator_local_zero_momentum_npy_v1"
APE_SMEAR_WORKFLOW_ID = "ape_smear_chroma_qio_npy_v1"
HYP_SMEAR_WORKFLOW_ID = "hyp_smear_chroma_qio_npy_v1"
WILSON_FLOW_WORKFLOW_ID = "wilson_flow_chroma_qio_energy_npy_v1"
STOUT_SMEAR_WORKFLOW_ID = "stout_smear_chroma_qio_npy_v1"
RHO_VECTOR_GAMMA_INSERTIONS = ["gamma1_gamma1", "gamma2_gamma2", "gamma3_gamma3"]
PROTON_2PT_FIXED_FIELDS = {
    "task_type": "proton_2pt",
    "workflow_id": PROTON_2PT_WORKFLOW_ID,
    "start_from": "gauge",
    "has_existing_propagators": False,
    "gauge_format": "chroma_qio",
    "fermion_action": "clover",
    "multigrid_blocks": [[6, 6, 6, 4], [4, 4, 4, 9]],
    "stout_smear_steps": 1,
    "stout_smear_rho": 0.125,
    "stout_smear_ndim": 4,
    "source_type": "wall",
    "sink_type": "local",
    "momentum_projection": "zero",
    "momenta": [[0, 0, 0]],
    "gauge_fixed": False,
    "correlator_output_format": "npy",
    "script_style": "complete",
}
PROTON_2PT_PROPAGATOR_FIXED_FIELDS = {
    "task_type": "proton_2pt",
    "workflow_id": PROTON_2PT_PROPAGATOR_WORKFLOW_ID,
    "start_from": "propagator",
    "has_existing_propagators": True,
    "source_type": "wall",
    "sink_type": "local",
    "momentum_projection": "zero",
    "momenta": [[0, 0, 0]],
    "gauge_fixed": False,
    "correlator_output_format": "npy",
    "script_style": "complete",
}


def _mom2_leq_9_family() -> list[list[int]]:
    momenta: list[list[int]] = []
    for npz in range(-3, 4):
        for npy in range(-3, 4):
            for npx in range(-3, 4):
                if npx * npx + npy * npy + npz * npz <= 9:
                    momenta.append([npx, npy, npz])
    return momenta


MESON_SPEC_MOMENTA = _mom2_leq_9_family()
MESON_SPEC_GAMMA_INSERTIONS = ["gamma5_gamma5", "gamma4gamma5_gamma4gamma5"]
MESON_SPEC_FIXED_FIELDS = {
    "task_type": "meson_spec",
    "workflow_id": MESON_SPEC_WORKFLOW_ID,
    "start_from": "gauge",
    "has_existing_propagators": False,
    "gauge_format": "chroma_qio",
    "fermion_action": "clover",
    "source_type": "wall",
    "sink_type": "local",
    "gamma_insertions": list(MESON_SPEC_GAMMA_INSERTIONS),
    "momentum_projection": "explicit",
    "momenta": [list(item) for item in MESON_SPEC_MOMENTA],
    "gauge_fixed": False,
    "correlator_output_format": "npy",
    "script_style": "complete",
}
MESON_SPEC_PROPAGATOR_FIXED_FIELDS = {
    "task_type": "meson_spec",
    "workflow_id": MESON_SPEC_PROPAGATOR_WORKFLOW_ID,
    "start_from": "propagator",
    "has_existing_propagators": True,
    "source_type": "wall",
    "sink_type": "local",
    "gamma_insertions": list(MESON_SPEC_GAMMA_INSERTIONS),
    "momentum_projection": "explicit",
    "momenta": [list(item) for item in MESON_SPEC_MOMENTA],
    "gauge_fixed": False,
    "correlator_output_format": "npy",
    "script_style": "complete",
}
QUARK_PROPAGATOR_FIXED_FIELDS = {
    "task_type": "quark_propagator",
    "workflow_id": QUARK_PROPAGATOR_WORKFLOW_ID,
    "start_from": "gauge",
    "has_existing_propagators": False,
    "gauge_format": "chroma_qio",
    "fermion_action": "clover",
    "multigrid_blocks": [[6, 6, 6, 4], [4, 4, 4, 9]],
    "stout_smear_steps": 1,
    "stout_smear_rho": 0.125,
    "stout_smear_ndim": 4,
    "source_type": "point",
    "sink_type": "propagator",
    "momentum_projection": "none",
    "momenta": [],
    "gauge_fixed": False,
    "correlator_output_format": "hdf5",
    "script_style": "complete",
}
QUARK_PROPAGATOR_GAUSSIAN_SHELL_FIXED_FIELDS = {
    "task_type": "quark_propagator",
    "workflow_id": QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID,
    "start_from": "gauge",
    "has_existing_propagators": False,
    "gauge_format": "chroma_qio",
    "fermion_action": "clover",
    "source_type": "point",
    "sink_type": "propagator",
    "momentum_projection": "none",
    "momenta": [],
    "gauge_fixed": False,
    "correlator_output_format": "hdf5",
    "script_style": "complete",
    "source_smearing_kind": "gaussian_shell",
    "source_smearing_rho": 2.0,
    "source_smearing_steps": 5,
}
RHO_VECTOR_FIXED_FIELDS = {
    "task_type": "rho_vector",
    "workflow_id": RHO_VECTOR_WORKFLOW_ID,
    "start_from": "gauge",
    "has_existing_propagators": False,
    "gauge_format": "chroma_qio",
    "fermion_action": "clover",
    "source_type": "wall",
    "sink_type": "local",
    "gamma_insertions": list(RHO_VECTOR_GAMMA_INSERTIONS),
    "momentum_projection": "zero",
    "momenta": [[0, 0, 0]],
    "gauge_fixed": False,
    "correlator_output_format": "npy",
    "script_style": "complete",
}
RHO_VECTOR_PROPAGATOR_FIXED_FIELDS = {
    "task_type": "rho_vector",
    "workflow_id": RHO_VECTOR_PROPAGATOR_WORKFLOW_ID,
    "start_from": "propagator",
    "has_existing_propagators": True,
    "source_type": "wall",
    "sink_type": "local",
    "gamma_insertions": list(RHO_VECTOR_GAMMA_INSERTIONS),
    "momentum_projection": "zero",
    "momenta": [[0, 0, 0]],
    "gauge_fixed": False,
    "correlator_output_format": "npy",
    "script_style": "complete",
}
APE_SMEAR_FIXED_FIELDS = {
    "task_type": "ape_smear",
    "workflow_id": APE_SMEAR_WORKFLOW_ID,
    "start_from": "gauge",
    "has_existing_propagators": False,
    "gauge_format": "chroma_qio",
    "source_type": "none",
    "sink_type": "gauge",
    "momentum_projection": "none",
    "momenta": [],
    "gauge_fixed": False,
    "correlator_output_format": "npy",
    "script_style": "complete",
}
HYP_SMEAR_FIXED_FIELDS = {
    "task_type": "hyp_smear",
    "workflow_id": HYP_SMEAR_WORKFLOW_ID,
    "start_from": "gauge",
    "has_existing_propagators": False,
    "gauge_format": "chroma_qio",
    "source_type": "none",
    "sink_type": "gauge",
    "momentum_projection": "none",
    "momenta": [],
    "gauge_fixed": False,
    "correlator_output_format": "npy",
    "script_style": "complete",
}
WILSON_FLOW_FIXED_FIELDS = {
    "task_type": "wilson_flow",
    "workflow_id": WILSON_FLOW_WORKFLOW_ID,
    "start_from": "gauge",
    "has_existing_propagators": False,
    "gauge_format": "chroma_qio",
    "source_type": "none",
    "sink_type": "gauge",
    "momentum_projection": "none",
    "momenta": [],
    "gauge_fixed": False,
    "correlator_output_format": "npy",
    "script_style": "complete",
}
STOUT_SMEAR_FIXED_FIELDS = {
    "task_type": "stout_smear",
    "workflow_id": STOUT_SMEAR_WORKFLOW_ID,
    "start_from": "gauge",
    "has_existing_propagators": False,
    "gauge_format": "chroma_qio",
    "stout_smear_steps": 1,
    "stout_smear_rho": 0.241,
    "stout_smear_ndim": 3,
    "source_type": "none",
    "sink_type": "gauge",
    "momentum_projection": "none",
    "momenta": [],
    "gauge_fixed": False,
    "correlator_output_format": "npy",
    "script_style": "complete",
}


@dataclass
class WorkflowMatchResult:
    matched: bool
    workflow_target: str | None = None
    task_type: str | None = None
    fixed_fields: dict[str, object] = field(default_factory=dict)
    mapping_notes: list[str] = field(default_factory=list)
    unsupported_reasons: list[str] = field(default_factory=list)
    local_references: list[str] = field(default_factory=list)
    external_citations: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _record(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _momentum_key(momentum: list[int]) -> tuple[int, int, int]:
    return tuple(int(item) for item in momentum)


def _check_conflict(draft: Pion2ptTaskDraft, field_name: str, expected: object, reasons: list[str], label: str) -> None:
    actual = getattr(draft, field_name)
    if actual in (None, [], {}):
        return
    if actual != expected:
        _record(reasons, f"Current supported workflow requires {label}={expected!r}, but the request specified {actual!r}.")


def _match_pion_2pt(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    if draft.start_from == "propagator" or draft.has_existing_propagators:
        return _match_pion_2pt_existing_propagator(draft)
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "gauge", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", False, reasons, "has_existing_propagators")
    _check_conflict(draft, "gauge_format", "chroma_qio", reasons, "gauge_format")
    _check_conflict(draft, "fermion_action", "clover", reasons, "fermion_action")
    _check_conflict(draft, "source_type", "wall", reasons, "source_type")
    _check_conflict(draft, "sink_type", "local", reasons, "sink_type")
    _check_conflict(draft, "momentum_projection", "zero", reasons, "momentum_projection")
    _check_conflict(draft, "correlator_output_format", "npy", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.momenta and draft.momenta != [[0, 0, 0]]:
        _record(reasons, "Current supported workflow requires zero momentum with momenta == [[0, 0, 0]].")
    if reasons:
        return WorkflowMatchResult(
            matched=False,
            unsupported_reasons=reasons,
        )
    return WorkflowMatchResult(
        matched=True,
        workflow_target=PION_2PT_WORKFLOW_ID,
        task_type="pion_2pt",
        fixed_fields=dict(PION_2PT_FIXED_FIELDS),
        mapping_notes=[
            "Confirmed pion two-point target mapped to the validated gauge -> Clover -> wall-source -> local-sink -> zero-momentum -> npy implementation path."
        ],
        local_references=list(PINNED_PION_2PT_PYQUDA_FILES),
        external_citations=load_physics_citations(PION_2PT_WORKFLOW_ID),
    )


def _match_pion_2pt_existing_propagator(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "propagator", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", True, reasons, "has_existing_propagators")
    _check_conflict(draft, "sink_type", "local", reasons, "sink_type")
    _check_conflict(draft, "momentum_projection", "zero", reasons, "momentum_projection")
    _check_conflict(draft, "correlator_output_format", "npy", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.propagator_format not in (None, "npy", "hdf5", "chroma_qio"):
        _record(reasons, "Current propagator-entry pion 2pt workflow only supports propagator formats grounded in local PyQUDA IO helpers: npy, hdf5, or chroma_qio.")
    if draft.source_type not in (None, "wall", "point"):
        _record(
            reasons,
            "Current propagator-entry pion 2pt workflow only supports source_type in {'wall', 'point'} based on local PyQUDA source conventions and stored propagator IO paths.",
        )
    if draft.momenta and draft.momenta != [[0, 0, 0]]:
        _record(reasons, "Current propagator-entry pion 2pt workflow requires zero momentum with momenta == [[0, 0, 0]].")
    if reasons:
        return WorkflowMatchResult(matched=False, unsupported_reasons=reasons)
    fixed_fields = dict(PION_2PT_PROPAGATOR_FIXED_FIELDS)
    if draft.source_type in {"wall", "point"}:
        fixed_fields["source_type"] = draft.source_type
    else:
        fixed_fields["source_type"] = "wall"
    return WorkflowMatchResult(
        matched=True,
        workflow_target=PION_2PT_PROPAGATOR_WORKFLOW_ID,
        task_type="pion_2pt",
        fixed_fields=fixed_fields,
        mapping_notes=[
            "Confirmed pion two-point target mapped to the validated existing-propagator -> zero-momentum local pseudoscalar contraction -> npy implementation path.",
            "The propagator-entry family preserves the stored source convention when it is explicitly grounded as wall or point.",
        ],
        local_references=[
            "tests/test_mesonspec.py",
            "tests/test_io.py",
            "pyquda_utils/io/__init__.py",
            "pyquda_utils/core.py",
            "pyquda_utils/gamma.py",
            "pyquda_utils/source.py",
            "examples/3_Pion_Proton_2pt.py",
        ],
        external_citations=load_physics_citations(PION_2PT_WORKFLOW_ID),
    )


def _match_pion_dispersion(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "gauge", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", False, reasons, "has_existing_propagators")
    _check_conflict(draft, "gauge_format", "chroma_qio", reasons, "gauge_format")
    _check_conflict(draft, "fermion_action", "clover", reasons, "fermion_action")
    _check_conflict(draft, "source_type", "point", reasons, "source_type")
    _check_conflict(draft, "sink_type", "local", reasons, "sink_type")
    _check_conflict(draft, "momentum_projection", "explicit", reasons, "momentum_projection")
    _check_conflict(draft, "correlator_output_format", "npy", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.gauge_fixed not in (None, False):
        _record(reasons, "Current supported pion-dispersion workflow assumes no gauge fixing step.")
    supported_momenta = {_momentum_key(item) for item in PION_DISPERSION_MOMENTA}
    unsupported_momenta = [momentum for momentum in draft.momenta if _momentum_key(momentum) not in supported_momenta]
    if unsupported_momenta:
        _record(
            reasons,
            "Current supported pion-dispersion workflow only accepts momentum vectors drawn from the locally grounded 9-momentum family in examples/5_Pion_Dispersion.py.",
        )
    if reasons:
        return WorkflowMatchResult(
            matched=False,
            unsupported_reasons=reasons,
        )
    fixed_fields = dict(PION_DISPERSION_FIXED_FIELDS)
    if draft.momenta:
        fixed_fields["momenta"] = [list(item) for item in draft.momenta]
        mapping_notes = [
            "Confirmed pion-dispersion target mapped to the validated gauge -> Clover -> point-source at spatial origin -> momentum-subset -> npy implementation path.",
            "The requested momentum list stays inside the locally grounded 9-momentum family from the PyQUDA dispersion example.",
        ]
    else:
        mapping_notes = [
            "Confirmed pion-dispersion target mapped to the validated gauge -> Clover -> point-source at spatial origin -> fixed momentum list -> npy implementation path."
        ]
    return WorkflowMatchResult(
        matched=True,
        workflow_target=PION_DISPERSION_WORKFLOW_ID,
        task_type="pion_dispersion",
        fixed_fields=fixed_fields,
        mapping_notes=mapping_notes,
        local_references=list(PINNED_PION_DISPERSION_PYQUDA_FILES),
        external_citations=load_physics_citations(PION_DISPERSION_WORKFLOW_ID),
    )


def _match_proton_2pt(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    if draft.start_from == "propagator" or draft.has_existing_propagators:
        return _match_proton_2pt_existing_propagator(draft)
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "gauge", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", False, reasons, "has_existing_propagators")
    _check_conflict(draft, "gauge_format", "chroma_qio", reasons, "gauge_format")
    _check_conflict(draft, "fermion_action", "clover", reasons, "fermion_action")
    _check_conflict(draft, "source_type", "wall", reasons, "source_type")
    _check_conflict(draft, "sink_type", "local", reasons, "sink_type")
    _check_conflict(draft, "momentum_projection", "zero", reasons, "momentum_projection")
    _check_conflict(draft, "gauge_fixed", False, reasons, "gauge_fixed")
    _check_conflict(draft, "correlator_output_format", "npy", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.momenta and draft.momenta != [[0, 0, 0]]:
        _record(reasons, "Current supported proton workflow requires zero momentum with momenta == [[0, 0, 0]].")
    if reasons:
        return WorkflowMatchResult(
            matched=False,
            unsupported_reasons=reasons,
        )
    return WorkflowMatchResult(
        matched=True,
        workflow_target=PROTON_2PT_WORKFLOW_ID,
        task_type="proton_2pt",
        fixed_fields=dict(PROTON_2PT_FIXED_FIELDS),
        mapping_notes=[
            "Confirmed proton two-point target mapped to the validated gauge -> stout-smear -> getDirac -> wall-source -> parity-projected zero-momentum -> npy implementation path."
        ],
        local_references=list(PINNED_PROTON_2PT_PYQUDA_FILES),
        external_citations=load_physics_citations(PROTON_2PT_WORKFLOW_ID),
    )


def _match_pion_pcac(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    if draft.start_from == "propagator" or draft.has_existing_propagators:
        return _match_pion_pcac_existing_propagator(draft)
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "gauge", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", False, reasons, "has_existing_propagators")
    _check_conflict(draft, "gauge_format", "chroma_qio", reasons, "gauge_format")
    _check_conflict(draft, "fermion_action", "clover", reasons, "fermion_action")
    _check_conflict(draft, "source_type", "wall", reasons, "source_type")
    _check_conflict(draft, "sink_type", "local", reasons, "sink_type")
    _check_conflict(draft, "momentum_projection", "zero", reasons, "momentum_projection")
    _check_conflict(draft, "gauge_fixed", False, reasons, "gauge_fixed")
    _check_conflict(draft, "correlator_output_format", "npy", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.momenta and draft.momenta != [[0, 0, 0]]:
        _record(reasons, "Current supported pion PCAC workflow requires zero momentum with momenta == [[0, 0, 0]].")
    if reasons:
        return WorkflowMatchResult(matched=False, unsupported_reasons=reasons)
    return WorkflowMatchResult(
        matched=True,
        workflow_target=PION_PCAC_WORKFLOW_ID,
        task_type="pion_pcac",
        fixed_fields=dict(PION_PCAC_FIXED_FIELDS),
        mapping_notes=[
            "Confirmed pion PCAC target mapped to the validated gauge -> stout-smear -> getDirac -> wall-source -> pion/pionA4 zero-momentum ratio -> npy implementation path."
        ],
        local_references=list(PINNED_PION_PCAC_PYQUDA_FILES),
        external_citations=load_physics_citations(PION_PCAC_WORKFLOW_ID),
    )


def _match_pion_pcac_existing_propagator(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "propagator", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", True, reasons, "has_existing_propagators")
    _check_conflict(draft, "source_type", "wall", reasons, "source_type")
    _check_conflict(draft, "sink_type", "local", reasons, "sink_type")
    _check_conflict(draft, "momentum_projection", "zero", reasons, "momentum_projection")
    _check_conflict(draft, "gauge_fixed", False, reasons, "gauge_fixed")
    _check_conflict(draft, "correlator_output_format", "npy", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.propagator_format not in (None, "npy", "hdf5", "chroma_qio"):
        _record(
            reasons,
            "Current propagator-entry pion PCAC workflow only supports propagator formats grounded in local PyQUDA IO helpers: npy, hdf5, or chroma_qio.",
        )
    if draft.momenta and draft.momenta != [[0, 0, 0]]:
        _record(reasons, "Current propagator-entry pion PCAC workflow requires zero momentum with momenta == [[0, 0, 0]].")
    if draft.source_timeslices and draft.propagator_paths and len(draft.source_timeslices) != len(draft.propagator_paths):
        _record(
            reasons,
            "Current propagator-entry pion PCAC workflow requires len(source_timeslices) == len(propagator_paths) so each stored propagator has an explicit source timeslice for the pion/pionA4 ratio contraction.",
        )
    if reasons:
        return WorkflowMatchResult(matched=False, unsupported_reasons=reasons)
    return WorkflowMatchResult(
        matched=True,
        workflow_target=PION_PCAC_PROPAGATOR_WORKFLOW_ID,
        task_type="pion_pcac",
        fixed_fields=dict(PION_PCAC_PROPAGATOR_FIXED_FIELDS),
        mapping_notes=[
            "Confirmed pion PCAC target mapped to the validated existing-propagator -> zero-momentum pion/pionA4 ratio -> npy implementation path.",
            "This narrow branch reuses local PyQUDA propagator IO helpers together with the exact pion/pionA4 contraction structure from the upstream PCAC example.",
        ],
        local_references=list(PINNED_PION_PCAC_PROPAGATOR_PYQUDA_FILES),
        external_citations=load_physics_citations(PION_PCAC_WORKFLOW_ID),
    )


def _match_proton_2pt_existing_propagator(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "propagator", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", True, reasons, "has_existing_propagators")
    _check_conflict(draft, "source_type", "wall", reasons, "source_type")
    _check_conflict(draft, "sink_type", "local", reasons, "sink_type")
    _check_conflict(draft, "momentum_projection", "zero", reasons, "momentum_projection")
    _check_conflict(draft, "gauge_fixed", False, reasons, "gauge_fixed")
    _check_conflict(draft, "correlator_output_format", "npy", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.propagator_format not in (None, "npy", "hdf5", "chroma_qio"):
        _record(
            reasons,
            "Current propagator-entry proton workflow only supports propagator formats grounded in local PyQUDA IO helpers: npy, hdf5, or chroma_qio.",
        )
    if draft.momenta and draft.momenta != [[0, 0, 0]]:
        _record(reasons, "Current propagator-entry proton workflow requires zero momentum with momenta == [[0, 0, 0]].")
    if draft.source_timeslices and draft.propagator_paths and len(draft.source_timeslices) != len(draft.propagator_paths):
        _record(
            reasons,
            "Current propagator-entry proton workflow requires len(source_timeslices) == len(propagator_paths) so each stored propagator has an explicit source timeslice for the parity-projected contraction.",
        )
    if reasons:
        return WorkflowMatchResult(matched=False, unsupported_reasons=reasons)
    return WorkflowMatchResult(
        matched=True,
        workflow_target=PROTON_2PT_PROPAGATOR_WORKFLOW_ID,
        task_type="proton_2pt",
        fixed_fields=dict(PROTON_2PT_PROPAGATOR_FIXED_FIELDS),
        mapping_notes=[
            "Confirmed proton two-point target mapped to the validated existing-propagator -> parity-projected zero-momentum proton contraction -> npy implementation path.",
            "This narrow branch reuses local PyQUDA propagator IO helpers and the exact proton contraction structure from the upstream proton example.",
        ],
        local_references=list(PINNED_PROTON_2PT_PROPAGATOR_PYQUDA_FILES),
        external_citations=load_physics_citations(PROTON_2PT_WORKFLOW_ID),
    )


def _match_meson_spec(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    if draft.start_from == "propagator" or draft.has_existing_propagators:
        return _match_meson_spec_existing_propagator(draft)
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "gauge", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", False, reasons, "has_existing_propagators")
    _check_conflict(draft, "gauge_format", "chroma_qio", reasons, "gauge_format")
    _check_conflict(draft, "fermion_action", "clover", reasons, "fermion_action")
    _check_conflict(draft, "source_type", "wall", reasons, "source_type")
    _check_conflict(draft, "sink_type", "local", reasons, "sink_type")
    _check_conflict(draft, "momentum_projection", "explicit", reasons, "momentum_projection")
    _check_conflict(draft, "gauge_fixed", False, reasons, "gauge_fixed")
    _check_conflict(draft, "correlator_output_format", "npy", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.gamma_insertions and draft.gamma_insertions != MESON_SPEC_GAMMA_INSERTIONS:
        _record(
            reasons,
            "Current meson-spectroscopy workflow only supports the fixed gamma insertion family {'gamma5_gamma5', 'gamma4gamma5_gamma4gamma5'}.",
        )
    supported_momenta = {_momentum_key(item) for item in MESON_SPEC_MOMENTA}
    unsupported_momenta = [momentum for momentum in draft.momenta if _momentum_key(momentum) not in supported_momenta]
    if unsupported_momenta:
        _record(
            reasons,
            "Current meson-spectroscopy workflow only accepts momentum vectors drawn from the locally grounded |p|^2<=9 family in tests/test_mesonspec.py.",
        )
    if reasons:
        return WorkflowMatchResult(matched=False, unsupported_reasons=reasons)
    fixed_fields = dict(MESON_SPEC_FIXED_FIELDS)
    if draft.momenta:
        fixed_fields["momenta"] = [list(item) for item in draft.momenta]
        mapping_notes = [
            "Confirmed meson-spectroscopy target mapped to the validated gauge -> Clover -> wall-source -> fixed gamma5/gamma4gamma5 insertion family -> grounded momentum-subset -> npy implementation path.",
            "The requested momentum list stays inside the locally grounded |p|^2<=9 family from tests/test_mesonspec.py.",
        ]
    else:
        mapping_notes = [
            "Confirmed meson-spectroscopy target mapped to the validated gauge -> Clover -> wall-source -> fixed gamma5/gamma4gamma5 insertion family -> full grounded |p|^2<=9 momentum family -> npy implementation path."
        ]
    return WorkflowMatchResult(
        matched=True,
        workflow_target=MESON_SPEC_WORKFLOW_ID,
        task_type="meson_spec",
        fixed_fields=fixed_fields,
        mapping_notes=mapping_notes,
        local_references=list(PINNED_MESON_SPEC_PYQUDA_FILES),
        external_citations=load_physics_citations(MESON_SPEC_WORKFLOW_ID),
    )


def _match_meson_spec_existing_propagator(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "propagator", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", True, reasons, "has_existing_propagators")
    _check_conflict(draft, "source_type", "wall", reasons, "source_type")
    _check_conflict(draft, "sink_type", "local", reasons, "sink_type")
    _check_conflict(draft, "momentum_projection", "explicit", reasons, "momentum_projection")
    _check_conflict(draft, "gauge_fixed", False, reasons, "gauge_fixed")
    _check_conflict(draft, "correlator_output_format", "npy", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.gamma_insertions and draft.gamma_insertions != MESON_SPEC_GAMMA_INSERTIONS:
        _record(
            reasons,
            "Current propagator-entry meson-spectroscopy workflow only supports the fixed gamma insertion family {'gamma5_gamma5', 'gamma4gamma5_gamma4gamma5'}.",
        )
    if draft.propagator_format not in (None, "npy", "hdf5", "chroma_qio"):
        _record(
            reasons,
            "Current propagator-entry meson-spectroscopy workflow only supports propagator formats grounded in local PyQUDA IO helpers: npy, hdf5, or chroma_qio.",
        )
    supported_momenta = {_momentum_key(item) for item in MESON_SPEC_MOMENTA}
    unsupported_momenta = [momentum for momentum in draft.momenta if _momentum_key(momentum) not in supported_momenta]
    if unsupported_momenta:
        _record(
            reasons,
            "Current propagator-entry meson-spectroscopy workflow only accepts momentum vectors drawn from the locally grounded |p|^2<=9 family in tests/test_mesonspec.py.",
        )
    if reasons:
        return WorkflowMatchResult(matched=False, unsupported_reasons=reasons)
    fixed_fields = dict(MESON_SPEC_PROPAGATOR_FIXED_FIELDS)
    if draft.momenta:
        fixed_fields["momenta"] = [list(item) for item in draft.momenta]
        mapping_notes = [
            "Confirmed meson-spectroscopy target mapped to the validated existing-propagator -> fixed gamma5/gamma4gamma5 insertion family -> grounded momentum-subset -> npy implementation path.",
            "This narrow branch reuses local PyQUDA propagator IO helpers together with the exact meson-spectroscopy contraction structure from tests/test_mesonspec.py.",
        ]
    else:
        mapping_notes = [
            "Confirmed meson-spectroscopy target mapped to the validated existing-propagator -> fixed gamma5/gamma4gamma5 insertion family -> full grounded |p|^2<=9 momentum family -> npy implementation path.",
            "This narrow branch reuses local PyQUDA propagator IO helpers together with the exact meson-spectroscopy contraction structure from tests/test_mesonspec.py.",
        ]
    return WorkflowMatchResult(
        matched=True,
        workflow_target=MESON_SPEC_PROPAGATOR_WORKFLOW_ID,
        task_type="meson_spec",
        fixed_fields=fixed_fields,
        mapping_notes=mapping_notes,
        local_references=list(PINNED_MESON_SPEC_PROPAGATOR_PYQUDA_FILES),
        external_citations=load_physics_citations(MESON_SPEC_WORKFLOW_ID),
    )


def _match_quark_propagator(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    request_text = f"{getattr(draft, 'user_request', '') or ''} {getattr(draft, 'notes', '') or ''}".lower()
    wants_gaussian_shell = getattr(draft, "source_smearing_kind", None) == "gaussian_shell" or any(
        token in request_text for token in ("gaussian shell", "gaussian-shell", "gaussian smeared", "gaussian-smeared", "shell source", "shell-source")
    )
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "gauge", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", False, reasons, "has_existing_propagators")
    _check_conflict(draft, "gauge_format", "chroma_qio", reasons, "gauge_format")
    _check_conflict(draft, "fermion_action", "clover", reasons, "fermion_action")
    _check_conflict(draft, "source_type", "point", reasons, "source_type")
    _check_conflict(draft, "sink_type", "propagator", reasons, "sink_type")
    _check_conflict(draft, "momentum_projection", "none", reasons, "momentum_projection")
    _check_conflict(draft, "gauge_fixed", False, reasons, "gauge_fixed")
    _check_conflict(draft, "correlator_output_format", "hdf5", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.momenta not in ([], None):
        _record(reasons, "Current quark-propagator workflow does not support momentum projection; momenta must stay empty.")
    if wants_gaussian_shell:
        _check_conflict(draft, "source_smearing_kind", "gaussian_shell", reasons, "source_smearing_kind")
        _check_conflict(draft, "source_smearing_rho", 2.0, reasons, "source_smearing_rho")
        _check_conflict(draft, "source_smearing_steps", 5, reasons, "source_smearing_steps")
    if reasons:
        return WorkflowMatchResult(matched=False, unsupported_reasons=reasons)
    if wants_gaussian_shell:
        return WorkflowMatchResult(
            matched=True,
            workflow_target=QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID,
            task_type="quark_propagator",
            fixed_fields=dict(QUARK_PROPAGATOR_GAUSSIAN_SHELL_FIXED_FIELDS),
            mapping_notes=[
                "Confirmed quark-propagator target mapped to the validated gauge -> point-source propagator -> gaussianSmear(rho=2.0, n_steps=5) -> getClover -> invertPropagator -> HDF5 path."
            ],
            local_references=list(PINNED_GAUSSIAN_SHELL_QUARK_PROPAGATOR_PYQUDA_FILES),
            external_citations=[],
        )
    return WorkflowMatchResult(
        matched=True,
        workflow_target=QUARK_PROPAGATOR_WORKFLOW_ID,
        task_type="quark_propagator",
        fixed_fields=dict(QUARK_PROPAGATOR_FIXED_FIELDS),
        mapping_notes=[
            "Confirmed quark-propagator target mapped to the validated gauge -> stout-smear -> getDirac -> point-source inversion -> HDF5 propagator path."
        ],
        local_references=list(PINNED_QUARK_PROPAGATOR_PYQUDA_FILES),
        external_citations=[],
    )


def _match_wilson_flow(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "gauge", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", False, reasons, "has_existing_propagators")
    _check_conflict(draft, "gauge_format", "chroma_qio", reasons, "gauge_format")
    _check_conflict(draft, "correlator_output_format", "npy", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.source_type not in (None, "none"):
        _record(reasons, "Current Wilson-flow workflow does not use source_type; leave it unspecified.")
    if draft.sink_type not in (None, "gauge"):
        _record(reasons, "Current Wilson-flow workflow does not use sink_type; leave it unspecified.")
    if draft.momentum_projection not in (None, "none"):
        _record(reasons, "Current Wilson-flow workflow does not use momentum projection.")
    if draft.momenta:
        _record(reasons, "Current Wilson-flow workflow does not use explicit momentum vectors.")
    if draft.has_existing_propagators:
        _record(reasons, "Current Wilson-flow workflow only supports starting from a gauge configuration.")
    if reasons:
        return WorkflowMatchResult(matched=False, unsupported_reasons=reasons)
    return WorkflowMatchResult(
        matched=True,
        workflow_target=WILSON_FLOW_WORKFLOW_ID,
        task_type="wilson_flow",
        fixed_fields=dict(WILSON_FLOW_FIXED_FIELDS),
        mapping_notes=[
            "Confirmed Wilson-flow target mapped to the validated gauge -> gauge.copy() -> wilsonFlowChroma(flow_steps, flow_epsilon) -> npy energy-history implementation path."
        ],
        local_references=list(PINNED_WILSON_FLOW_PYQUDA_FILES),
        external_citations=[],
    )


def _match_rho_vector(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    if draft.start_from == "propagator" or draft.has_existing_propagators:
        return _match_rho_vector_existing_propagator(draft)
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "gauge", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", False, reasons, "has_existing_propagators")
    _check_conflict(draft, "gauge_format", "chroma_qio", reasons, "gauge_format")
    _check_conflict(draft, "fermion_action", "clover", reasons, "fermion_action")
    _check_conflict(draft, "source_type", "wall", reasons, "source_type")
    _check_conflict(draft, "sink_type", "local", reasons, "sink_type")
    _check_conflict(draft, "momentum_projection", "zero", reasons, "momentum_projection")
    _check_conflict(draft, "gauge_fixed", False, reasons, "gauge_fixed")
    _check_conflict(draft, "correlator_output_format", "npy", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.gamma_insertions and draft.gamma_insertions != RHO_VECTOR_GAMMA_INSERTIONS:
        _record(
            reasons,
            "Current rho/vector workflow only supports gamma_insertions == ['gamma1_gamma1', 'gamma2_gamma2', 'gamma3_gamma3'].",
        )
    if draft.momenta and draft.momenta != [[0, 0, 0]]:
        _record(reasons, "Current rho/vector workflow requires zero momentum with momenta == [[0, 0, 0]].")
    if reasons:
        return WorkflowMatchResult(matched=False, unsupported_reasons=reasons)
    return WorkflowMatchResult(
        matched=True,
        workflow_target=RHO_VECTOR_WORKFLOW_ID,
        task_type="rho_vector",
        fixed_fields=dict(RHO_VECTOR_FIXED_FIELDS),
        mapping_notes=[
            "Confirmed rho/vector target mapped to the validated gauge -> Clover -> wall-source -> local-sink -> spatial gamma_i family -> zero-momentum -> npy implementation path."
        ],
        local_references=list(PINNED_RHO_VECTOR_PYQUDA_FILES),
        external_citations=[],
    )


def _match_rho_vector_existing_propagator(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "propagator", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", True, reasons, "has_existing_propagators")
    _check_conflict(draft, "source_type", "wall", reasons, "source_type")
    _check_conflict(draft, "sink_type", "local", reasons, "sink_type")
    _check_conflict(draft, "momentum_projection", "zero", reasons, "momentum_projection")
    _check_conflict(draft, "gauge_fixed", False, reasons, "gauge_fixed")
    _check_conflict(draft, "correlator_output_format", "npy", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.gamma_insertions and draft.gamma_insertions != RHO_VECTOR_GAMMA_INSERTIONS:
        _record(
            reasons,
            "Current propagator-entry rho/vector workflow only supports gamma_insertions == ['gamma1_gamma1', 'gamma2_gamma2', 'gamma3_gamma3'].",
        )
    if draft.propagator_format not in (None, "npy", "hdf5", "chroma_qio"):
        _record(
            reasons,
            "Current propagator-entry rho/vector workflow only supports propagator formats grounded in local PyQUDA IO helpers: npy, hdf5, or chroma_qio.",
        )
    if draft.momenta and draft.momenta != [[0, 0, 0]]:
        _record(reasons, "Current propagator-entry rho/vector workflow requires zero momentum with momenta == [[0, 0, 0]].")
    if draft.source_timeslices and draft.propagator_paths and len(draft.source_timeslices) != len(draft.propagator_paths):
        _record(
            reasons,
            "Current propagator-entry rho/vector workflow requires len(source_timeslices) == len(propagator_paths) so each stored propagator has an explicit source timeslice for the zero-momentum vector contraction.",
        )
    if reasons:
        return WorkflowMatchResult(matched=False, unsupported_reasons=reasons)
    return WorkflowMatchResult(
        matched=True,
        workflow_target=RHO_VECTOR_PROPAGATOR_WORKFLOW_ID,
        task_type="rho_vector",
        fixed_fields=dict(RHO_VECTOR_PROPAGATOR_FIXED_FIELDS),
        mapping_notes=[
            "Confirmed rho/vector target mapped to the validated existing-propagator -> fixed spatial gamma_i family -> zero-momentum -> npy implementation path.",
            "This narrow branch reuses local PyQUDA propagator IO helpers together with the exact mesonspec tensor contraction pattern for the spatial vector bilinear family.",
        ],
        local_references=list(PINNED_RHO_VECTOR_PROPAGATOR_PYQUDA_FILES),
        external_citations=[],
    )


def _match_ape_smear(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "gauge", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", False, reasons, "has_existing_propagators")
    _check_conflict(draft, "gauge_format", "chroma_qio", reasons, "gauge_format")
    _check_conflict(draft, "source_type", "none", reasons, "source_type")
    _check_conflict(draft, "sink_type", "gauge", reasons, "sink_type")
    _check_conflict(draft, "momentum_projection", "none", reasons, "momentum_projection")
    _check_conflict(draft, "gauge_fixed", False, reasons, "gauge_fixed")
    _check_conflict(draft, "correlator_output_format", "npy", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.momenta not in (None, []):
        _record(reasons, "Current APE-smear workflow does not use explicit momentum vectors.")
    if draft.has_existing_propagators:
        _record(reasons, "Current APE-smear workflow only supports starting from a gauge configuration.")
    if reasons:
        return WorkflowMatchResult(matched=False, unsupported_reasons=reasons)
    return WorkflowMatchResult(
        matched=True,
        workflow_target=APE_SMEAR_WORKFLOW_ID,
        task_type="ape_smear",
        fixed_fields=dict(APE_SMEAR_FIXED_FIELDS),
        mapping_notes=[
            "Confirmed APE-smear target mapped to the validated gauge -> gauge.copy() -> apeSmearChroma(1, 2.5, 4) -> npy smeared-gauge implementation path."
        ],
        local_references=list(PINNED_APE_SMEAR_PYQUDA_FILES),
        external_citations=[],
    )


def _match_hyp_smear(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "gauge", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", False, reasons, "has_existing_propagators")
    _check_conflict(draft, "gauge_format", "chroma_qio", reasons, "gauge_format")
    _check_conflict(draft, "source_type", "none", reasons, "source_type")
    _check_conflict(draft, "sink_type", "gauge", reasons, "sink_type")
    _check_conflict(draft, "momentum_projection", "none", reasons, "momentum_projection")
    _check_conflict(draft, "gauge_fixed", False, reasons, "gauge_fixed")
    _check_conflict(draft, "correlator_output_format", "npy", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.momenta not in (None, []):
        _record(reasons, "Current HYP-smear workflow does not use explicit momentum vectors.")
    if draft.has_existing_propagators:
        _record(reasons, "Current HYP-smear workflow only supports starting from a gauge configuration.")
    if reasons:
        return WorkflowMatchResult(matched=False, unsupported_reasons=reasons)
    return WorkflowMatchResult(
        matched=True,
        workflow_target=HYP_SMEAR_WORKFLOW_ID,
        task_type="hyp_smear",
        fixed_fields=dict(HYP_SMEAR_FIXED_FIELDS),
        mapping_notes=[
            "Confirmed HYP-smear target mapped to the validated gauge -> gauge.copy() -> hypSmear(1, 0.75, 0.6, 0.3, 4) -> npy smeared-gauge implementation path."
        ],
        local_references=list(PINNED_HYP_SMEAR_PYQUDA_FILES),
        external_citations=[],
    )


def _match_stout_smear(draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    reasons: list[str] = []
    _check_conflict(draft, "start_from", "gauge", reasons, "start_from")
    _check_conflict(draft, "has_existing_propagators", False, reasons, "has_existing_propagators")
    _check_conflict(draft, "gauge_format", "chroma_qio", reasons, "gauge_format")
    _check_conflict(draft, "source_type", "none", reasons, "source_type")
    _check_conflict(draft, "sink_type", "gauge", reasons, "sink_type")
    _check_conflict(draft, "momentum_projection", "none", reasons, "momentum_projection")
    _check_conflict(draft, "gauge_fixed", False, reasons, "gauge_fixed")
    _check_conflict(draft, "correlator_output_format", "npy", reasons, "correlator_output_format")
    _check_conflict(draft, "script_style", "complete", reasons, "script_style")
    if draft.momenta not in (None, []):
        _record(reasons, "Current stout-smear workflow does not use explicit momentum vectors.")
    if draft.stout_smear_steps not in (None, 1):
        _record(reasons, "Current stout-smear workflow is fixed to stout_smear_steps=1 from tests/test_smear.py.")
    if draft.stout_smear_rho not in (None, 0.241):
        _record(reasons, "Current stout-smear workflow is fixed to stout_smear_rho=0.241 from tests/test_smear.py.")
    if draft.stout_smear_ndim not in (None, 3):
        _record(reasons, "Current stout-smear workflow is fixed to stout_smear_ndim=3 from tests/test_smear.py.")
    if draft.has_existing_propagators:
        _record(reasons, "Current stout-smear workflow only supports starting from a gauge configuration.")
    if reasons:
        return WorkflowMatchResult(matched=False, unsupported_reasons=reasons)
    return WorkflowMatchResult(
        matched=True,
        workflow_target=STOUT_SMEAR_WORKFLOW_ID,
        task_type="stout_smear",
        fixed_fields=dict(STOUT_SMEAR_FIXED_FIELDS),
        mapping_notes=[
            "Confirmed stout-smear target mapped to the validated gauge -> gauge.copy() -> stoutSmear(1, 0.241, 3) -> npy smeared-gauge implementation path."
        ],
        local_references=list(PINNED_STOUT_SMEAR_PYQUDA_FILES),
        external_citations=[],
    )


def match_supported_workflow(physics: PhysicsTargetArtifact, draft: Pion2ptTaskDraft) -> WorkflowMatchResult:
    confirmed = physics.confirmed_interpretation
    if confirmed is None:
        return WorkflowMatchResult(
            matched=False,
            unsupported_reasons=["Physics target is not confirmed yet."],
        )

    target_id = confirmed.get("target_id")
    if target_id == PION_TARGET_ID:
        return _match_pion_2pt(draft)
    if target_id == PION_PCAC_TARGET_ID:
        return _match_pion_pcac(draft)
    if target_id == PION_DISPERSION_TARGET_ID:
        return _match_pion_dispersion(draft)
    if target_id == MESON_SPEC_TARGET_ID:
        return _match_meson_spec(draft)
    if target_id == PROTON_TARGET_ID:
        return _match_proton_2pt(draft)
    if target_id == NEUTRON_TARGET_ID:
        return WorkflowMatchResult(
            matched=False,
            unsupported_reasons=[
                "Confirmed neutron two-point correlator target is not implemented in the current grounded local workflow catalog. "
                "Nearest grounded baryon alternatives are proton_2pt_chroma_wall_local_zero_momentum_npy_v1 and "
                "proton_2pt_existing_propagator_local_zero_momentum_npy_v1."
            ],
        )
    if target_id == QUARK_PROPAGATOR_TARGET_ID:
        return _match_quark_propagator(draft)
    if target_id == RHO_TARGET_ID:
        return _match_rho_vector(draft)
    if target_id == APE_SMEAR_TARGET_ID:
        return _match_ape_smear(draft)
    if target_id == HYP_SMEAR_TARGET_ID:
        return _match_hyp_smear(draft)
    if target_id == WILSON_FLOW_TARGET_ID:
        return _match_wilson_flow(draft)
    if target_id == STOUT_SMEAR_TARGET_ID:
        return _match_stout_smear(draft)
    if target_id not in {
        PION_TARGET_ID,
        PION_PCAC_TARGET_ID,
        PION_DISPERSION_TARGET_ID,
        MESON_SPEC_TARGET_ID,
        PROTON_TARGET_ID,
        NEUTRON_TARGET_ID,
        QUARK_PROPAGATOR_TARGET_ID,
        RHO_TARGET_ID,
        APE_SMEAR_TARGET_ID,
        HYP_SMEAR_TARGET_ID,
        WILSON_FLOW_TARGET_ID,
        STOUT_SMEAR_TARGET_ID,
    }:
        return WorkflowMatchResult(
            matched=False,
            unsupported_reasons=[f"Confirmed physics target {target_id!r} is not implemented yet."],
        )
    raise AssertionError("Unreachable workflow branch")


def apply_workflow_match(
    draft: Pion2ptTaskDraft,
    physics: PhysicsTargetArtifact,
    match: WorkflowMatchResult,
) -> None:
    if not match.matched:
        return
    physics.chosen_workflow_target = match.workflow_target
    physics.fixed_by_workflow_fields.update(match.fixed_fields)
    draft.chosen_workflow_target = match.workflow_target
    draft.pyquda_references = list(match.local_references)
    draft.external_citations = list(match.external_citations)
    for field_name, value in match.fixed_fields.items():
        if getattr(draft, field_name) in (None, [], {}):
            setattr(draft, field_name, value)
            draft.field_sources[field_name] = "fixed"
        draft.fixed_fields[field_name] = value
