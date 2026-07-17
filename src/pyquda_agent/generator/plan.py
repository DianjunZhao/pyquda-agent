"""Build a reference-grounded implementation plan for supported runnable workflows."""

from __future__ import annotations

from pathlib import Path

from pyquda_agent.intent.schema import PhysicsTargetArtifact
from pyquda_agent.models import ContextBundle
from pyquda_agent.models import ImplementationPlan
from pyquda_agent.retrieval.physics_citations import load_physics_citations
from pyquda_agent.tasks.clarifier import determine_missing_fields
from pyquda_agent.tasks.schema import Pion2ptTaskDraft
from pyquda_agent.workflows.matcher import WorkflowMatchResult
from scripts.check_pyquda_runtime import build_report as build_runtime_report


def _normalize_runtime_evidence(runtime_report: dict | None, *, references: list[dict]) -> dict | None:
    if runtime_report is None:
        return None
    report = dict(runtime_report)
    env_ready = bool(report.get("ready"))
    structurally_grounded = bool(references)
    blockers: list[str] = []
    if not structurally_grounded:
        blockers.append("No concrete local PyQUDA references were attached to the implementation plan.")
    blockers.extend(report.get("evidence_levels", {}).get("blockers", []))
    report["syntax_valid"] = True
    report["reference_grounded"] = structurally_grounded
    report["environment_ready"] = env_ready
    report["runtime_proved"] = False
    report["runtime_level"] = "runtime_ready" if env_ready else ("structurally_grounded" if structurally_grounded else "environment_missing")
    report["evidence_levels"] = {
        "syntax_valid": True,
        "structurally_grounded": structurally_grounded,
        "runtime_ready": env_ready,
        "runtime_proved": False,
        "current_level": report["runtime_level"],
        "blockers": blockers,
    }
    report["probe_policy"] = {
        "auto_run": False,
        "reason": "Generated-script probes are not run automatically because a complete script may start a real inversion workload.",
    }
    report["environment_probe"] = {
        "script": "scripts/check_pyquda_runtime.py",
        "used_repo_pythonpath": bool(report.get("used_repo_pythonpath")),
    }
    return report


def _find_reference_summary(references: list[dict], suffix: str) -> dict | None:
    for ref in references:
        if ref["path"].endswith(suffix):
            return ref
    return None


def _build_handoff_contract(draft: Pion2ptTaskDraft) -> dict:
    input_paths: list[str] = []
    input_manifest: list[dict] = []
    if draft.gauge_path:
        input_paths.append(draft.gauge_path)
        input_manifest.append(
            {
                "kind": "gauge",
                "path": draft.gauge_path,
            }
        )
    for index, path in enumerate(draft.propagator_paths):
        if path:
            input_paths.append(path)
            input_manifest.append(
                {
                    "kind": "propagator",
                    "path": path,
                    "index": index,
                    "source_timeslice": draft.source_timeslices[index] if index < len(draft.source_timeslices) else None,
                }
            )

    script_path = draft.script_output_path or ""
    probe_artifact = str(Path(script_path).with_suffix(".probe.json")) if script_path else None
    output_paths = {
        "script": script_path or None,
        "probe_artifact": probe_artifact,
    }
    if draft.task_type == "quark_propagator":
        output_paths["propagator"] = draft.correlator_output_path or None
    elif draft.task_type == "ape_smear":
        output_paths["smeared_gauge"] = draft.correlator_output_path or None
    elif draft.task_type == "stout_smear":
        output_paths["smeared_gauge"] = draft.correlator_output_path or None
    elif draft.task_type == "wilson_flow":
        output_paths["energy_history"] = draft.correlator_output_path or None
    else:
        output_paths["correlator"] = draft.correlator_output_path or None

    input_kind = "propagator" if draft.start_from == "propagator" else "gauge"
    preflight_checks = [
        f"Ensure all {input_kind} inputs are visible from every rank before launch.",
        "Ensure the output directory is writable by the rank that saves the final correlator artifact.",
        "Confirm the nearest existing parent of each emitted artifact path is writable on the target filesystem before submission.",
        "Verify numpy, cupy, pyquda_utils, and pyquda import successfully before starting a full inversion job.",
        "Review the sibling .physics.json, .task.json, and .plan.json artifacts before cluster submission.",
    ]
    if draft.start_from == "gauge":
        preflight_checks.append(
            "Keep gauge inputs on shared read-only storage and write new outputs to a dedicated writable results directory when possible."
        )
    if draft.start_from == "propagator":
        preflight_checks.extend(
            [
                "Verify the propagator input manifest matches the intended source-timeslice ordering before launch.",
                "Treat propagator inputs as immutable handoff artifacts; do not reuse an input path as an output path.",
                "Prefer a dedicated writable results directory instead of writing new outputs beside stored propagator handoff artifacts.",
            ]
        )

    return {
        "cluster_launch": draft.cluster_launch,
        "resource_path": draft.resource_path,
        "start_from": draft.start_from,
        "input_paths": input_paths,
        "input_manifest": input_manifest,
        "input_mutability_policy": "immutable_inputs_never_overwritten",
        "output_paths": output_paths,
        "input_visibility": "all_ranks",
        "output_writer_policy": "rank0_only",
        "required_modules": ["numpy", "cupy", "pyquda_utils", "pyquda"],
        "preflight_checks": preflight_checks,
        "submission_assumption": "Launch under an MPI/GPU layout consistent with GRID_SIZE and the target PyQUDA environment.",
    }


def _build_wilson_flow_convention_decisions(references: list[dict]) -> list[dict]:
    decisions: list[dict] = []

    flow_ref = _find_reference_summary(references, "tests/test_wflow.py")
    if flow_ref is not None:
        decisions.append(
            {
                "category": "physics",
                "decision": "Use the narrow Wilson-flow gauge-evolution path and record the returned energy history.",
                "why": "The supported family is pinned to the exact local test_wflow path rather than a generalized flow-observable framework.",
                "references": [flow_ref["path"]],
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
                "decision": "Read the gauge with io.readQIOGauge and save the final energy history as npy.",
                "why": "The narrow implementation path stays grounded in the local IO helpers already used by the upstream tests.",
                "references": io_refs,
                "citations": [],
            }
        )

    return decisions


def _build_ape_smear_convention_decisions(references: list[dict]) -> list[dict]:
    decisions: list[dict] = []

    smear_ref = _find_reference_summary(references, "tests/test_smear.py")
    if smear_ref is not None:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Use the narrow local gauge-smearing path: read a Chroma/QIO gauge, copy it, and apply apeSmearChroma(1, 2.5, 4).",
                "why": "The supported APE-smear family is intentionally pinned to the exact local test_smear path rather than generalized smearing parameters or alternative gauge-smearing families.",
                "references": [smear_ref["path"]],
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
                "decision": "Read the input gauge with io.readQIOGauge and save the APE-smeared gauge with io.writeNPYGauge.",
                "why": "The complete script should stay inside the local grounded IO helper family already used by upstream tests.",
                "references": io_refs,
                "citations": [],
            }
        )

    return decisions


def _build_hyp_smear_convention_decisions(references: list[dict]) -> list[dict]:
    decisions: list[dict] = []

    smear_ref = _find_reference_summary(references, "tests/test_smear.py")
    if smear_ref is not None:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Use the narrow local gauge-smearing path: read a Chroma/QIO gauge, copy it, and apply hypSmear(1, 0.75, 0.6, 0.3, 4).",
                "why": "The supported HYP-smear family is intentionally pinned to the exact local test_smear path rather than generalized smearing parameters or alternative gauge-smearing families.",
                "references": [smear_ref["path"]],
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
                "decision": "Read the input gauge with io.readQIOGauge and save the HYP-smeared gauge with io.writeNPYGauge.",
                "why": "The complete script should stay inside the local grounded IO helper family already used by upstream tests.",
                "references": io_refs,
                "citations": [],
            }
        )

    return decisions


def _build_stout_smear_convention_decisions(references: list[dict]) -> list[dict]:
    decisions: list[dict] = []

    smear_ref = _find_reference_summary(references, "tests/test_smear.py")
    if smear_ref is not None:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Use the narrow local gauge-smearing path: read a Chroma/QIO gauge, copy it, and apply stoutSmear(1, 0.241, 3).",
                "why": "The supported stout-smear family is intentionally pinned to the exact local test_smear path rather than generalized smearing options such as APE or HYP.",
                "references": [smear_ref["path"]],
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
                "decision": "Read the input gauge with io.readQIOGauge and save the smeared gauge with io.writeNPYGauge.",
                "why": "The complete script should stay inside the local grounded IO helper family already used by upstream tests.",
                "references": io_refs,
                "citations": [],
            }
        )

    return decisions


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
                "why": "The grounded workflow uses the same QIO gauge-loading path exercised in the local IO test and helper module.",
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


def _build_dispersion_convention_decisions(references: list[dict], external_citations: list[dict]) -> list[dict]:
    citation_ids = {item["id"] for item in external_citations}
    decisions: list[dict] = []

    point_ref = _find_reference_summary(references, "examples/5_Pion_Dispersion.py")
    if point_ref is not None:
        decisions.append(
            {
                "category": "physics",
                "decision": "Use a point source at the fixed spatial origin with a user-specified source timeslice.",
                "why": "The narrow pion-dispersion workflow follows the local PyQUDA example that builds momentum-projected pion correlators from a point source.",
                "references": [point_ref["path"]],
                "citations": [],
            }
        )

    momentum_refs = []
    for suffix in ("examples/5_Pion_Dispersion.py", "tests/test_mesonspec.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            momentum_refs.append(ref["path"])
    if momentum_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Use MomentumPhase with a momentum list drawn from the locally validated 9-momentum family in the pion-dispersion example.",
                "why": "The supported dispersion family stays grounded in the explicit momentum-phase construction already present in local PyQUDA references, while allowing reviewable subsets of that same local momentum family.",
                "references": momentum_refs,
                "citations": [],
            }
        )

    contraction_refs = []
    for suffix in ("examples/5_Pion_Dispersion.py", "pyquda_utils/gamma.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            contraction_refs.append(ref["path"])
    if contraction_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Contract the propagator with gamma5 bilinears and momentum phases to produce a momentum-indexed pion correlator array.",
                "why": "This mirrors the contraction pattern of the local pion-dispersion example without inventing new helper APIs.",
                "references": contraction_refs,
                "citations": [],
            }
        )

    dispersion_citations = []
    for citation_id in ("bulava-2022-hadron-spectroscopy",):
        if citation_id in citation_ids:
            dispersion_citations.append(citation_id)
    if dispersion_citations or momentum_refs:
        decisions.append(
            {
                "category": "physics",
                "decision": "Treat the workflow as a momentum-projected pion two-point path for dispersion analysis, not a generic nonzero-momentum correlator generator.",
                "why": "The implementation target is intentionally pinned to one local PyQUDA example and one locally grounded momentum family so that complete mode remains fully grounded even when the user asks for a subset of the validated momentum list.",
                "references": momentum_refs,
                "citations": dispersion_citations,
            }
        )

    return decisions


def _build_pion_pcac_convention_decisions(references: list[dict], external_citations: list[dict]) -> list[dict]:
    decisions: list[dict] = []

    pcac_ref = _find_reference_summary(references, "examples/4_Pion_PCAC.py")
    if pcac_ref is not None:
        decisions.append(
            {
                "category": "physics",
                "decision": "Use the narrow pion PCAC ratio built from pseudoscalar and temporal-axial zero-momentum correlators.",
                "why": "The supported family is pinned to the exact local PyQUDA PCAC example rather than a generalized axial-current workflow.",
                "references": [pcac_ref["path"]],
                "citations": [item["id"] for item in external_citations],
            }
        )

    io_refs = []
    for suffix in ("examples/4_Pion_PCAC.py", "tests/test_io.py", "pyquda_utils/io/__init__.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            io_refs.append(ref["path"])
    if io_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Read a Chroma/QIO gauge, apply one stout-smear step, then load it into a getDirac-based Clover operator.",
                "why": "This matches the exact setup path used by the local PCAC example and preserves the grounded stout-smear/getDirac implementation choices.",
                "references": io_refs,
                "citations": [],
            }
        )

    contraction_refs = []
    for suffix in ("examples/4_Pion_PCAC.py", "pyquda_utils/gamma.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            contraction_refs.append(ref["path"])
    if contraction_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Contract both pion and pionA4 channels with gamma5/gamma4gamma5 factors and report the derived PCAC ratio in one reviewable npy artifact.",
                "why": "The fixed complete path should stay traceable to the local contraction structure instead of inventing a higher-level helper API.",
                "references": contraction_refs,
                "citations": [],
            }
        )

    return decisions


def _build_pion_pcac_propagator_convention_decisions(references: list[dict], external_citations: list[dict]) -> list[dict]:
    decisions: list[dict] = []

    pcac_ref = _find_reference_summary(references, "examples/4_Pion_PCAC.py")
    if pcac_ref is not None:
        decisions.append(
            {
                "category": "physics",
                "decision": "Use the narrow pion PCAC ratio built from pseudoscalar and temporal-axial zero-momentum correlators.",
                "why": "The supported branch keeps the same local PyQUDA PCAC observable, but starts from stored wall-source propagators instead of regenerating them from a gauge field.",
                "references": [pcac_ref["path"]],
                "citations": [item["id"] for item in external_citations],
            }
        )

    io_refs = []
    for suffix in ("tests/test_io.py", "pyquda_utils/io/__init__.py", "examples/4_Pion_PCAC.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            io_refs.append(ref["path"])
    if io_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Read stored propagators through grounded local PyQUDA IO helpers instead of rerunning the Clover inversion path.",
                "why": "This branch is intentionally limited to propagator formats already exercised by the local IO helper stack so complete mode remains traceable and reviewable.",
                "references": io_refs,
                "citations": [],
            }
        )

    contraction_refs = []
    for suffix in ("examples/4_Pion_PCAC.py", "pyquda_utils/gamma.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            contraction_refs.append(ref["path"])
    if contraction_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Contract both pion and pionA4 channels with gamma5/gamma4gamma5 factors, then save [pion, pionA4, ratio] in one reviewable npy artifact.",
                "why": "The complete branch should stay close to the upstream PCAC contraction structure while making the stored-propagator entry path explicit for HPC handoff.",
                "references": contraction_refs,
                "citations": [],
            }
        )

    return decisions


def _build_quark_propagator_convention_decisions(references: list[dict]) -> list[dict]:
    decisions: list[dict] = []

    example_ref = _find_reference_summary(references, "examples/2_Quark_Propagator.py")
    if example_ref is not None:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Use the local example path: read Chroma/QIO gauge, stout-smear once, build getDirac, and invert a point source at [0,0,0,t_src].",
                "why": "The complete script is intentionally pinned to the existing upstream quark-propagator example instead of inventing a new inversion helper path.",
                "references": [example_ref["path"]],
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
                "decision": "Save the propagator as HDF5 with the same grounded save/load path exercised in the local IO test.",
                "why": "The supported output format is traced to the existing HDF5 propagator save/load path already validated by upstream test_io.",
                "references": io_refs,
                "citations": [],
            }
        )

    source_refs = []
    for suffix in ("pyquda_utils/source.py", "pyquda_utils/core.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            source_refs.append(ref["path"])
    if source_refs:
        decisions.append(
            {
                "category": "physics",
                "decision": "Fix the source convention to a point source at the spatial origin with user-specified t_src.",
                "why": "This keeps the workflow narrow and traceable to the local source helpers plus the upstream quark-propagator example.",
                "references": source_refs,
                "citations": [],
            }
        )

    return decisions


def _build_gaussian_shell_quark_propagator_convention_decisions(references: list[dict]) -> list[dict]:
    decisions: list[dict] = []

    gaussian_ref = _find_reference_summary(references, "tests/test_gaussian.py")
    if gaussian_ref is not None:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Use the local Gaussian-shell path: build a point-source propagator, apply source.gaussianSmear(rho=2.0, n_steps=5), then invert with getClover + invertPropagator.",
                "why": "The complete script is intentionally pinned to the existing upstream Gaussian test instead of inventing a generalized shell-source interface.",
                "references": [gaussian_ref["path"]],
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
                "decision": "Save the Gaussian-shell propagator as HDF5 with the same grounded save/load path exercised in the local IO test.",
                "why": "The supported output format is traced to the existing HDF5 propagator save/load path already validated by upstream test_io.",
                "references": io_refs,
                "citations": [],
            }
        )

    source_refs = []
    for suffix in ("pyquda_utils/source.py", "pyquda_utils/core.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            source_refs.append(ref["path"])
    if source_refs:
        decisions.append(
            {
                "category": "physics",
                "decision": "Fix the source convention to a point-source seed at the spatial origin, then apply the grounded Gaussian shell-source helper with rho=2.0 and n_steps=5.",
                "why": "This keeps the workflow narrow and traceable to the local source/core helpers plus the upstream Gaussian regression path.",
                "references": source_refs,
                "citations": [],
            }
        )

    return decisions


def _build_meson_spec_convention_decisions(references: list[dict], external_citations: list[dict]) -> list[dict]:
    citation_ids = {item["id"] for item in external_citations}
    decisions: list[dict] = []

    meson_ref = _find_reference_summary(references, "tests/test_mesonspec.py")
    if meson_ref is not None:
        decisions.append(
            {
                "category": "physics",
                "decision": "Use the fixed wall-source meson-spectroscopy path with gamma5 and gamma4gamma5 insertion channels.",
                "why": "The supported workflow is intentionally pinned to the exact correlator family already encoded in the local PyQUDA mesonspec test.",
                "references": [meson_ref["path"]],
                "citations": [item["id"] for item in external_citations],
            }
        )

    phase_refs = []
    for suffix in ("tests/test_mesonspec.py", "pyquda_utils/phase.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            phase_refs.append(ref["path"])
    if phase_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Use MomentumPhase with the grounded |p|^2<=9 momentum family from phase.getMomList(9).",
                "why": "This keeps the workflow traceable to the exact local momentum-family construction used in the upstream mesonspec reference.",
                "references": phase_refs,
                "citations": [],
            }
        )

    gamma_refs = []
    for suffix in ("tests/test_mesonspec.py", "pyquda_utils/gamma.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            gamma_refs.append(ref["path"])
    if gamma_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Contract the propagator with the fixed gamma5/gamma4gamma5 bilinear family using CuPy einsum over the local mesonspec tensor layout.",
                "why": "The complete script should mirror the local mesonspec contraction path instead of inventing a generic spectroscopy helper API.",
                "references": gamma_refs,
                "citations": [],
            }
        )

    if meson_ref is not None or citation_ids:
        decisions.append(
            {
                "category": "physics",
                "decision": "Keep this family narrow: gauge entry, Clover, wall source, fixed gamma insertion family, grounded momentum family, and npy tensor output.",
                "why": "The goal is one fully grounded meson-spectroscopy path, not a shallow generic meson-correlator template.",
                "references": [meson_ref["path"]] if meson_ref is not None else [],
                "citations": [citation_id for citation_id in ("bulava-2022-hadron-spectroscopy",) if citation_id in citation_ids],
            }
        )

    return decisions


def _build_proton_convention_decisions(references: list[dict], external_citations: list[dict]) -> list[dict]:
    decisions: list[dict] = []

    proton_ref = _find_reference_summary(references, "examples/3_Pion_Proton_2pt.py")
    if proton_ref is not None:
        decisions.append(
            {
                "category": "physics",
                "decision": "Use a wall source at the requested source timeslice and contract a zero-momentum proton two-point correlator with the standard epsilon-color proton operator.",
                "why": "The supported proton workflow is intentionally pinned to the exact source/contraction family already encoded in the local PyQUDA proton example.",
                "references": [proton_ref["path"]],
                "citations": [item["id"] for item in external_citations],
            }
        )
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Apply one stout-smearing step and build the Dirac operator with core.getDirac plus the fixed multigrid block layout from the local example.",
                "why": "The current proton path must stay traceable to the existing runnable PyQUDA example rather than inventing a new baryon setup.",
                "references": [proton_ref["path"]],
                "citations": [],
            }
        )

    contraction_refs = []
    for suffix in ("examples/3_Pion_Proton_2pt.py", "pyquda_utils/core.py", "pyquda_utils/gamma.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            contraction_refs.append(ref["path"])
    if contraction_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Use the local parity-projected proton contraction with Cgamma5 spin coupling, color permutations, and core.gatherLattice reduction over spatial sites.",
                "why": "This mirrors the concrete contraction pattern in the upstream proton example and avoids inventing baryon helper APIs that are not present in PyQUDA.",
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
                "decision": "Read the gauge from a Chroma/QIO path and write the proton correlator as a rank-0 .npy artifact for HPC handoff.",
                "why": "The supported proton workflow keeps the same gauge IO family as the local examples and existing workflow suite.",
                "references": io_refs,
                "citations": [],
            }
        )

    return decisions


def _build_proton_propagator_convention_decisions(references: list[dict], external_citations: list[dict]) -> list[dict]:
    decisions: list[dict] = []

    proton_ref = _find_reference_summary(references, "examples/3_Pion_Proton_2pt.py")
    io_refs = []
    for suffix in ("tests/test_io.py", "pyquda_utils/io/__init__.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            io_refs.append(ref["path"])
    contraction_refs = []
    for suffix in ("examples/3_Pion_Proton_2pt.py", "pyquda_utils/gamma.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            contraction_refs.append(ref["path"])

    if io_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Load stored propagators through the grounded local IO helpers (NPY/HDF5/Chroma-QIO) and treat them as the handoff boundary instead of regenerating inversions.",
                "why": "The new proton propagator-entry branch must stay traceable to the local IO tests and helper module rather than inventing a new serialization path.",
                "references": io_refs,
                "citations": [],
            }
        )

    if proton_ref is not None:
        decisions.append(
            {
                "category": "physics",
                "decision": "Keep the same zero-momentum proton operator and parity-projected contraction as the local proton example, but consume precomputed wall-source propagators instead of rebuilding them from a gauge field.",
                "why": "This preserves the locally grounded proton physics path while exposing a narrow HPC handoff branch that starts from stored propagators.",
                "references": [proton_ref["path"]],
                "citations": [item["id"] for item in external_citations],
            }
        )

    if contraction_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Reuse the same Cgamma5 spin coupling, color permutations, and gather-and-roll postprocessing from the upstream proton example for each stored source timeslice.",
                "why": "This keeps the contraction code placeholder-free and faithful to the only grounded local proton contraction path.",
                "references": contraction_refs,
                "citations": [],
            }
        )

    return decisions


def _build_rho_vector_convention_decisions(references: list[dict], external_citations: list[dict]) -> list[dict]:
    decisions: list[dict] = []

    meson_ref = _find_reference_summary(references, "tests/test_mesonspec.py")
    xml_ref = _find_reference_summary(references, "tests/test_mesonspec.ini.xml")
    gamma_ref = _find_reference_summary(references, "pyquda_utils/gamma.py")
    core_ref = _find_reference_summary(references, "pyquda_utils/core.py")
    io_refs = []
    for suffix in ("tests/test_io.py", "pyquda_utils/io/__init__.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            io_refs.append(ref["path"])

    if meson_ref is not None or xml_ref is not None:
        ref_paths = [ref["path"] for ref in (meson_ref, xml_ref) if ref is not None]
        decisions.append(
            {
                "category": "physics",
                "decision": "Use the narrow rho/vector channel with spatial bilinears O_rho,i = qbar gamma_i q, zero momentum, wall source, and local sink.",
                "why": "The operator choice is standard model inference, while the runnable path stays pinned to the local mesonspec contraction structure and the upstream rho_x channel evidence in the XML reference.",
                "references": ref_paths,
                "citations": [item["id"] for item in external_citations],
            }
        )

    contraction_refs = [ref["path"] for ref in (meson_ref, gamma_ref, core_ref) if ref is not None]
    if contraction_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Mirror the local mesonspec contraction path with core.invert(dirac, 'wall', t_src), gamma.gamma(1/2/4), and CuPy einsum over the local propagator tensor layout.",
                "why": "The complete script must stay traceable to concrete local PyQUDA code instead of inventing a generic rho helper API.",
                "references": contraction_refs,
                "citations": [],
            }
        )

    if io_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Read the input gauge through the Chroma/QIO helper family and write a rank-0 npy tensor ordered as [source_timeslice, t, gamma_i].",
                "why": "This keeps the rho/vector path aligned with the grounded local IO conventions already used by the other supported workflows.",
                "references": io_refs,
                "citations": [],
            }
        )

    return decisions


def _build_rho_vector_propagator_convention_decisions(references: list[dict], external_citations: list[dict]) -> list[dict]:
    decisions: list[dict] = []

    meson_ref = _find_reference_summary(references, "tests/test_mesonspec.py")
    gamma_ref = _find_reference_summary(references, "pyquda_utils/gamma.py")
    io_refs = []
    for suffix in ("tests/test_io.py", "pyquda_utils/io/__init__.py"):
        ref = _find_reference_summary(references, suffix)
        if ref is not None:
            io_refs.append(ref["path"])

    if meson_ref is not None:
        decisions.append(
            {
                "category": "physics",
                "decision": "Keep the same narrow rho/vector channel with spatial bilinears O_rho,i = qbar gamma_i q and zero momentum, but consume precomputed wall-source propagators instead of rebuilding inversions.",
                "why": "This preserves the locally grounded rho/vector physics path while exposing a narrow HPC handoff branch that starts from stored propagators.",
                "references": [meson_ref["path"]],
                "citations": [item["id"] for item in external_citations],
            }
        )

    if io_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Load stored propagators through the grounded local IO helpers (NPY/HDF5/Chroma-QIO) and treat them as the handoff boundary instead of regenerating inversions.",
                "why": "The new rho/vector propagator-entry branch must stay traceable to the local IO tests and helper module rather than inventing a new serialization path.",
                "references": io_refs,
                "citations": [],
            }
        )

    contraction_refs = [ref["path"] for ref in (meson_ref, gamma_ref) if ref is not None]
    if contraction_refs:
        decisions.append(
            {
                "category": "pyquda",
                "decision": "Reuse the mesonspec tensor contraction with gamma.gamma(1/2/4), spatial gamma_i labels, and source-timeslice roll/gather postprocessing for each stored propagator.",
                "why": "This keeps the propagator-entry rho/vector branch placeholder-free and faithful to the only grounded local vector-channel contraction structure.",
                "references": contraction_refs,
                "citations": [],
            }
        )

    return decisions


def _build_clarification_trace(
    draft: Pion2ptTaskDraft,
    physics: PhysicsTargetArtifact,
    asked_questions: list[dict],
) -> list[dict]:
    clarified_fields = {field_name for field_name, source in draft.field_sources.items() if source == "clarified"}
    trace: list[dict] = []
    for item in asked_questions:
        field_name = item.get("field_name")
        scope = item.get("scope", "task")
        if scope == "physics":
            resolution = physics.clarified_fields.get(field_name.replace("_id", ""))
            if field_name == "confirmed_target_id":
                resolution = (physics.confirmed_interpretation or {}).get("target_id")
            trace.append(
                {
                    "field_name": field_name,
                    "answer": item.get("answer"),
                    "resolution": resolution,
                    "category": item.get("category", "physics"),
                    "scope": "physics",
                }
            )
            continue
        if field_name not in clarified_fields:
            continue
        trace.append(
            {
                "field_name": field_name,
                "answer": item.get("answer"),
                "resolution": getattr(draft, field_name, None),
                "category": item.get("category"),
                "scope": "task",
            }
        )
    return trace


def build_implementation_plan(
    draft: Pion2ptTaskDraft,
    physics: PhysicsTargetArtifact,
    workflow_match: WorkflowMatchResult,
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
    external_citations = physics.external_citations or workflow_match.external_citations or load_physics_citations(
        draft.workflow_id or "unknown"
    )
    runtime_readiness = build_runtime_report(pyquda_repo, use_repo_pythonpath=False) if pyquda_repo is not None else None
    runtime_readiness = _normalize_runtime_evidence(runtime_readiness, references=references)

    workflow_id = draft.workflow_id or "unknown"
    if workflow_id == "pion_dispersion_chroma_point_momentum_npy_v1":
        convention_decisions = _build_dispersion_convention_decisions(references, external_citations)
    elif workflow_id == "pion_pcac_chroma_wall_local_zero_momentum_npy_v1":
        convention_decisions = _build_pion_pcac_convention_decisions(references, external_citations)
    elif workflow_id == "pion_pcac_existing_propagator_local_zero_momentum_npy_v1":
        convention_decisions = _build_pion_pcac_propagator_convention_decisions(references, external_citations)
    elif workflow_id == "quark_propagator_chroma_point_hdf5_v1":
        convention_decisions = _build_quark_propagator_convention_decisions(references)
    elif workflow_id == "quark_propagator_gaussian_shell_chroma_hdf5_v1":
        convention_decisions = _build_gaussian_shell_quark_propagator_convention_decisions(references)
    elif workflow_id == "ape_smear_chroma_qio_npy_v1":
        convention_decisions = _build_ape_smear_convention_decisions(references)
    elif workflow_id == "hyp_smear_chroma_qio_npy_v1":
        convention_decisions = _build_hyp_smear_convention_decisions(references)
    elif workflow_id == "stout_smear_chroma_qio_npy_v1":
        convention_decisions = _build_stout_smear_convention_decisions(references)
    elif workflow_id == "wilson_flow_chroma_qio_energy_npy_v1":
        convention_decisions = _build_wilson_flow_convention_decisions(references)
    elif workflow_id in {
        "meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1",
        "meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1",
    }:
        convention_decisions = _build_meson_spec_convention_decisions(references, external_citations)
    elif workflow_id == "proton_2pt_chroma_wall_local_zero_momentum_npy_v1":
        convention_decisions = _build_proton_convention_decisions(references, external_citations)
    elif workflow_id == "proton_2pt_existing_propagator_local_zero_momentum_npy_v1":
        convention_decisions = _build_proton_propagator_convention_decisions(references, external_citations)
    elif workflow_id == "rho_vector_chroma_wall_local_zero_momentum_npy_v1":
        convention_decisions = _build_rho_vector_convention_decisions(references, external_citations)
    elif workflow_id == "rho_vector_existing_propagator_local_zero_momentum_npy_v1":
        convention_decisions = _build_rho_vector_propagator_convention_decisions(references, external_citations)
    else:
        convention_decisions = _build_convention_decisions(references, external_citations)

    field_resolution = dict(draft.field_sources)
    field_resolution["_resolution_buckets"] = {
        "user_confirmed_fields": dict(getattr(draft, "user_confirmed_fields", {})),
        "clarified_fields": dict(getattr(draft, "clarified_fields", {})),
        "inferred_fields": dict(getattr(draft, "inferred_fields", {})),
        "parser_guesses": dict(getattr(draft, "parser_guesses", {})),
        "fixed_fields": dict(getattr(draft, "fixed_fields", {})),
        "inherited_fields": dict(getattr(draft, "inherited_fields", {})),
    }
    field_resolution["_physics_resolution_buckets"] = {
        "user_confirmed_fields": dict(physics.user_confirmed_fields),
        "clarified_fields": dict(physics.clarified_fields),
        "inferred_fields": dict(physics.inferred_fields),
        "parser_guesses": dict(physics.parser_guesses),
        "fixed_by_workflow_fields": dict(physics.fixed_by_workflow_fields),
        "inherited_fields": dict(physics.inherited_fields),
    }

    return ImplementationPlan(
        workflow_id=workflow_id,
        task_type=draft.task_type or "unknown",
        user_request=physics.user_request,
        inferred_interpretation=physics.inferred_interpretation,
        confirmed_interpretation=physics.confirmed_interpretation,
        chosen_workflow_target=workflow_match.workflow_target,
        workflow_match=workflow_match.to_dict(),
        knowledge_boundary=dict(physics.knowledge_boundary),
        references=references,
        local_references_used=list(workflow_match.local_references or draft.pyquda_references),
        external_citations=external_citations,
        external_lookup=dict(physics.external_lookup),
        convention_decisions=convention_decisions,
        clarification_trace=_build_clarification_trace(draft, physics, asked_questions or []),
        runtime_readiness=runtime_readiness,
        handoff_contract=_build_handoff_contract(draft),
        physics_choices={
            "target_id": (physics.confirmed_interpretation or physics.inferred_interpretation or {}).get("target_id"),
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
            "flow_steps": draft.flow_steps,
            "flow_epsilon": draft.flow_epsilon,
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
            "multigrid_blocks": draft.multigrid_blocks,
            "stout_smear_steps": draft.stout_smear_steps,
            "stout_smear_rho": draft.stout_smear_rho,
            "stout_smear_ndim": draft.stout_smear_ndim,
        },
        runtime_choices={
            "cluster_launch": draft.cluster_launch,
            "script_output_path": draft.script_output_path,
            "correlator_output_path": draft.correlator_output_path,
            "primary_output_path": draft.correlator_output_path,
        },
        validation_checks=[
            "generated code is syntax-valid",
            "task fields fully resolved",
            "workflow matches supported runnable path",
            "generated code imports real PyQUDA APIs",
            "generated code matches local examples/tests/io helpers for the chosen workflow",
            "generated code contains no TODO/pass/placeholder text",
        ],
        field_resolution=field_resolution,
        inherited_session_fields=dict(getattr(draft, "inherited_fields", {})),
        unresolved_fields=list(draft.missing_fields),
        unsupported_reasons=list(dict.fromkeys([*physics.unsupported_reasons, *draft.unsupported_reasons, *workflow_match.unsupported_reasons])),
    )
