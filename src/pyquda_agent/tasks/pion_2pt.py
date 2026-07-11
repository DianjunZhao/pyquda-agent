"""Pion 2pt task finalization helpers."""

from __future__ import annotations

from .clarifier import determine_missing_fields
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
    return Pion2ptTask(
        task_type=draft.task_type,
        workflow_id=draft.workflow_id,
        start_from=draft.start_from,
        has_existing_propagators=draft.has_existing_propagators,
        gauge_format=draft.gauge_format,
        gauge_path=draft.gauge_path,
        propagator_format=draft.propagator_format,
        propagator_paths=list(draft.propagator_paths),
        lattice_size=list(draft.lattice_size),
        grid_size=list(draft.grid_size),
        fermion_action=draft.fermion_action,
        mass=draft.mass,
        xi_0=draft.xi_0,
        nu=draft.nu,
        coeff_t=draft.coeff_t,
        coeff_r=draft.coeff_r,
        solver_tol=draft.solver_tol,
        solver_maxiter=draft.solver_maxiter,
        source_type=draft.source_type,
        sink_type=draft.sink_type,
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
