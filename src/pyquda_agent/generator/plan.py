"""Build a reference-grounded implementation plan for runnable pion 2pt generation."""

from __future__ import annotations

from pyquda_agent.models import ContextBundle
from pyquda_agent.models import ImplementationPlan
from pyquda_agent.retrieval.physics_citations import load_physics_citations
from pyquda_agent.tasks.clarifier import determine_missing_fields
from pyquda_agent.tasks.schema import Pion2ptTaskDraft
from scripts.check_pyquda_runtime import build_report as build_runtime_report


def _find_reference_summary(references: list[dict], suffix: str) -> dict | None:
    for ref in references:
        if ref["path"].endswith(suffix):
            return ref
    return None


def _build_convention_decisions(references: list[dict], external_citations: list[dict]) -> list[dict]:
    citation_ids = {item["id"] for item in external_citations}
    decisions: list[dict] = []

    wall_ref = _find_reference_summary(references, "tests/test_mesonspec.py")
    if wall_ref is not None:
        decisions.append(
            {
                "category": "physics",
                "decision": "Use wall source at a specified source timeslice.",
                "why": "The fixed v1 workflow follows the local meson-spec test pattern for wall-source propagator generation.",
                "references": [wall_ref["path"]],
                "citations": [],
            }
        )

    contraction_refs = []
    for suffix in ("tests/test_mesonspec.py", "examples/3_Pion_Proton_2pt.py", "pyquda_utils/gamma.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            contraction_refs.append(ref["path"])
    if contraction_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Use the gamma5-based zero-momentum pion contraction written with CuPy einsum.",
                "why": "The contraction shape and gamma-matrix usage are grounded in the local meson-spec test and pion example, with gamma helpers from pyquda_utils.gamma.",
                "references": contraction_refs,
                "citations": [],
            }
        )

    io_refs = []
    for suffix in ("tests/test_io.py", "pyquda_utils/io/__init__.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            io_refs.append(ref["path"])
    if io_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Read the input gauge with io.readQIOGauge from a Chroma/QIO gauge path.",
                "why": "The fixed workflow uses the same QIO gauge-loading path exercised in the local IO test and helper module.",
                "references": io_refs,
                "citations": [],
            }
        )

    zero_momentum_refs = []
    for suffix in ("examples/5_Pion_Dispersion.py", "tests/test_mesonspec.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            zero_momentum_refs.append(ref["path"])
    zero_momentum_citations = []
    for citation_id in ("bulava-2022-hadron-spectroscopy", "howarth-giedt-2015-sigma"):
        if citation_id in citation_ids:
            zero_momentum_citations.append(citation_id)
    if zero_momentum_refs or zero_momentum_citations:
        decisions.append(
            {
                "category": "physics",
                "decision": "Restrict v1 to a single pion two-point correlator at zero momentum.",
                "why": "The local examples separate zero-momentum and dispersion workflows; the external citations justify the narrow two-point zero-momentum convention.",
                "references": zero_momentum_refs,
                "citations": zero_momentum_citations,
            }
        )

    return decisions


def _build_clarification_trace(draft: Pion2ptTaskDraft, asked_questions: list[dict]) -> list[dict]:
    clarified_fields = {field_name for field_name, source in draft.field_sources.items() if source == "clarified"}
    trace: list[dict] = []
    for item in asked_questions:
        field_name = item.get("field_name")
        if field_name not in clarified_fields:
            continue
        trace.append(
            {
                "field_name": field_name,
                "answer": item.get("answer"),
                "resolution": getattr(draft, field_name, None),
            }
        )
    return trace


def build_implementation_plan(
    draft: Pion2ptTaskDraft,
    context: ContextBundle,
    asked_questions: list[dict] | None = None,
    pyquda_repo=None,
) -> ImplementationPlan:
    determine_missing_fields(draft)
    references = []
    seen_paths: set[str] = set()
    for snippet in context.snippets:
        if snippet.source != "pyquda":
            continue
        if snippet.path in seen_paths:
            continue
        seen_paths.add(snippet.path)
        references.append(
            {
                "path": snippet.path,
                "source": snippet.source,
                "summary": snippet.summary,
            }
        )
    external_citations = load_physics_citations(draft.workflow_id or "unknown")
    runtime_readiness = build_runtime_report(pyquda_repo, use_repo_pythonpath=False) if pyquda_repo is not None else None

    return ImplementationPlan(
        workflow_id=draft.workflow_id or "unknown",
        task_type=draft.task_type or "unknown",
        references=references,
        external_citations=external_citations,
        convention_decisions=_build_convention_decisions(references, external_citations),
        clarification_trace=_build_clarification_trace(draft, asked_questions or []),
        runtime_readiness=runtime_readiness,
        physics_choices={
            "source_type": draft.source_type,
            "sink_type": draft.sink_type,
            "momentum_projection": draft.momentum_projection,
            "momenta": draft.momenta,
            "source_timeslices": draft.source_timeslices,
            "gauge_fixed": draft.gauge_fixed,
            "fermion_action": draft.fermion_action,
            "mass": draft.mass,
            "xi_0": draft.xi_0,
            "nu": draft.nu,
            "coeff_t": draft.coeff_t,
            "coeff_r": draft.coeff_r,
        },
        pyquda_choices={
            "start_from": draft.start_from,
            "gauge_format": draft.gauge_format,
            "gauge_path": draft.gauge_path,
            "lattice_size": draft.lattice_size,
            "grid_size": draft.grid_size,
            "resource_path": draft.resource_path,
            "solver_tol": draft.solver_tol,
            "solver_maxiter": draft.solver_maxiter,
            "output_format": draft.correlator_output_format,
        },
        runtime_choices={
            "cluster_launch": draft.cluster_launch,
            "script_output_path": draft.script_output_path,
            "correlator_output_path": draft.correlator_output_path,
        },
        validation_checks=[
            "task fields fully resolved",
            "workflow matches supported runnable path",
            "generated code imports real PyQUDA APIs",
            "generated code matches local examples/tests/io helpers for the fixed workflow",
            "generated code contains no TODO/pass/placeholder text",
        ],
        field_resolution=dict(draft.field_sources),
        unresolved_fields=list(draft.missing_fields),
        unsupported_reasons=list(draft.unsupported_reasons),
    )
