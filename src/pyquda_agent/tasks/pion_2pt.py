"""Pion 2pt task finalization helpers."""

from __future__ import annotations

from .clarifier import determine_missing_fields
from .clarifier import APE_SMEAR_WORKFLOW_ID
from .clarifier import HYP_SMEAR_WORKFLOW_ID
from .clarifier import MESON_SPEC_PROPAGATOR_WORKFLOW_ID
from .clarifier import PION_2PT_PROPAGATOR_WORKFLOW_ID
from .clarifier import PION_PCAC_PROPAGATOR_WORKFLOW_ID
from .clarifier import PROTON_2PT_PROPAGATOR_WORKFLOW_ID
from .clarifier import QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID
from .clarifier import RHO_VECTOR_PROPAGATOR_WORKFLOW_ID
from .clarifier import RHO_VECTOR_WORKFLOW_ID
from .clarifier import STOUT_SMEAR_WORKFLOW_ID
from .clarifier import WILSON_FLOW_WORKFLOW_ID
from .schema import Pion2ptTask
from .schema import Pion2ptTaskDraft


def finalize_task(draft: Pion2ptTaskDraft) -> Pion2ptTask:
    missing = determine_missing_fields(draft)
    if missing:
        raise ValueError(f"Cannot finalize task with missing fields: {', '.join(missing)}")
    if draft.unsupported_reasons:
        raise ValueError("Cannot finalize unsupported workflow: " + "; ".join(draft.unsupported_reasons))
    assert draft.task_type is not None
    assert draft.workflow_id is not None
    assert draft.start_from is not None
    assert draft.has_existing_propagators is not None
    assert draft.source_type is not None
    assert draft.sink_type is not None
    assert draft.momentum_projection is not None
    assert draft.gauge_fixed is not None
    assert draft.correlator_output_format is not None
    assert draft.correlator_output_path is not None
    assert draft.resource_path is not None
    assert draft.cluster_launch is not None
    assert draft.script_output_path is not None
    assert draft.script_style is not None
    if draft.workflow_id not in {
        PION_2PT_PROPAGATOR_WORKFLOW_ID,
        PION_PCAC_PROPAGATOR_WORKFLOW_ID,
        MESON_SPEC_PROPAGATOR_WORKFLOW_ID,
        PROTON_2PT_PROPAGATOR_WORKFLOW_ID,
        RHO_VECTOR_PROPAGATOR_WORKFLOW_ID,
        RHO_VECTOR_WORKFLOW_ID,
        QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID,
        APE_SMEAR_WORKFLOW_ID,
        HYP_SMEAR_WORKFLOW_ID,
        WILSON_FLOW_WORKFLOW_ID,
        STOUT_SMEAR_WORKFLOW_ID,
    }:
        assert draft.gauge_format is not None
        assert draft.gauge_path is not None
        assert draft.fermion_action is not None
        assert draft.mass is not None
        assert draft.xi_0 is not None
        assert draft.nu is not None
        assert draft.coeff_t is not None
        assert draft.coeff_r is not None
        assert draft.solver_tol is not None
        assert draft.solver_maxiter is not None
    if draft.workflow_id == WILSON_FLOW_WORKFLOW_ID:
        assert draft.gauge_format is not None
        assert draft.gauge_path is not None
        assert draft.flow_steps is not None
        assert draft.flow_epsilon is not None
    if draft.workflow_id == APE_SMEAR_WORKFLOW_ID:
        assert draft.gauge_format is not None
        assert draft.gauge_path is not None
    if draft.workflow_id == HYP_SMEAR_WORKFLOW_ID:
        assert draft.gauge_format is not None
        assert draft.gauge_path is not None
    if draft.workflow_id == STOUT_SMEAR_WORKFLOW_ID:
        assert draft.gauge_format is not None
        assert draft.gauge_path is not None
    return Pion2ptTask(
        task_type=draft.task_type,
        workflow_id=draft.workflow_id,
        start_from=draft.start_from,
        has_existing_propagators=draft.has_existing_propagators,
        gauge_format=draft.gauge_format or "chroma_qio",
        gauge_path=draft.gauge_path or "",
        propagator_format=draft.propagator_format,
        propagator_paths=list(draft.propagator_paths),
        lattice_size=list(draft.lattice_size),
        grid_size=list(draft.grid_size),
        fermion_action=draft.fermion_action or "clover",
        mass=draft.mass if draft.mass is not None else 0.0,
        xi_0=draft.xi_0 if draft.xi_0 is not None else 1.0,
        nu=draft.nu if draft.nu is not None else 1.0,
        coeff_t=draft.coeff_t if draft.coeff_t is not None else 1.0,
        coeff_r=draft.coeff_r if draft.coeff_r is not None else 1.0,
        solver_tol=draft.solver_tol if draft.solver_tol is not None else 1e-12,
        solver_maxiter=draft.solver_maxiter if draft.solver_maxiter is not None else 1000,
        multigrid_blocks=[list(item) for item in draft.multigrid_blocks],
        stout_smear_steps=draft.stout_smear_steps,
        stout_smear_rho=draft.stout_smear_rho,
        stout_smear_ndim=draft.stout_smear_ndim,
        source_smearing_kind=draft.source_smearing_kind,
        source_smearing_rho=draft.source_smearing_rho,
        source_smearing_steps=draft.source_smearing_steps,
        flow_steps=draft.flow_steps,
        flow_epsilon=draft.flow_epsilon,
        source_type=draft.source_type,
        sink_type=draft.sink_type,
        gamma_insertions=list(draft.gamma_insertions),
        momentum_projection=draft.momentum_projection,
        momenta=[list(item) for item in draft.momenta],
        source_timeslices=list(draft.source_timeslices),
        gauge_fixed=draft.gauge_fixed,
        correlator_output_format=draft.correlator_output_format,
        correlator_output_path=draft.correlator_output_path,
        resource_path=draft.resource_path,
        cluster_launch=draft.cluster_launch,
        script_output_path=draft.script_output_path,
        script_style=draft.script_style,
        field_sources=dict(draft.field_sources),
        notes=draft.notes,
    )
