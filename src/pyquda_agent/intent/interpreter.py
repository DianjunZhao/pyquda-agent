"""Interpret rough user requests into candidate physics targets."""

from __future__ import annotations

import re

from pyquda_agent.retrieval.physics_citations import load_physics_citations

from .schema import PhysicsTargetArtifact


PION_TARGET_ID = "pion_two_point_correlator"
PION_PCAC_TARGET_ID = "pion_pcac_ratio_correlator"
PION_DISPERSION_TARGET_ID = "pion_dispersion_correlator"
PROTON_TARGET_ID = "proton_two_point_correlator"
NEUTRON_TARGET_ID = "neutron_two_point_correlator"
MESON_SPEC_TARGET_ID = "meson_spectrum_correlator"
QUARK_PROPAGATOR_TARGET_ID = "quark_propagator"
WILSON_FLOW_TARGET_ID = "wilson_flow_energy_observable"
STOUT_SMEAR_TARGET_ID = "stout_smeared_gauge_configuration"
APE_SMEAR_TARGET_ID = "ape_smeared_gauge_configuration"
HYP_SMEAR_TARGET_ID = "hyp_smeared_gauge_configuration"
RHO_TARGET_ID = "rho_vector_meson_correlator"
MESON_UNSPECIFIED_TARGET_ID = "meson_two_point_correlator_unspecified"
BARYON_UNSPECIFIED_TARGET_ID = "baryon_two_point_correlator_unspecified"
HADRON_UNSPECIFIED_TARGET_ID = "hadron_two_point_correlator_unspecified"
PION_CITATION_KEY = "pion_2pt_chroma_wall_local_zero_momentum_npy_v1"
PION_PCAC_CITATION_KEY = "pion_pcac_chroma_wall_local_zero_momentum_npy_v1"
PION_DISPERSION_CITATION_KEY = "pion_dispersion_chroma_point_momentum_npy_v1"
PROTON_CITATION_KEY = "proton_2pt_chroma_wall_local_zero_momentum_npy_v1"
MESON_SPEC_CITATION_KEY = "meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1"
PION_LOCAL_REFERENCE_SUFFIXES = (
    "examples/3_Pion_Proton_2pt.py",
    "examples/5_Pion_Dispersion.py",
    "tests/test_mesonspec.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/source.py",
    "pyquda_utils/gamma.py",
)
PION_DISPERSION_LOCAL_REFERENCE_SUFFIXES = (
    "examples/5_Pion_Dispersion.py",
    "tests/test_mesonspec.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/source.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
)
PION_PCAC_LOCAL_REFERENCE_SUFFIXES = (
    "examples/4_Pion_PCAC.py",
    "examples/3_Pion_Proton_2pt.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
)
PROTON_LOCAL_REFERENCE_SUFFIXES = (
    "examples/3_Pion_Proton_2pt.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/source.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
)
MESON_SPEC_LOCAL_REFERENCE_SUFFIXES = (
    "tests/test_mesonspec.py",
    "tests/test_mesonspec.ini.xml",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
    "pyquda_utils/phase.py",
)
RHO_LOCAL_REFERENCE_SUFFIXES = (
    "tests/test_mesonspec.py",
    "tests/test_mesonspec.ini.xml",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
)
QUARK_PROPAGATOR_LOCAL_REFERENCE_SUFFIXES = (
    "examples/2_Quark_Propagator.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/source.py",
    "pyquda_utils/core.py",
)
QUARK_PROPAGATOR_GAUSSIAN_SHELL_LOCAL_REFERENCE_SUFFIXES = (
    "tests/test_gaussian.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/source.py",
    "pyquda_utils/core.py",
    "examples/2_Quark_Propagator.py",
)
APE_SMEAR_LOCAL_REFERENCE_SUFFIXES = (
    "tests/test_smear.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
)
HYP_SMEAR_LOCAL_REFERENCE_SUFFIXES = (
    "tests/test_smear.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
)
WILSON_FLOW_LOCAL_REFERENCE_SUFFIXES = (
    "tests/test_wflow.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
)
STOUT_SMEAR_LOCAL_REFERENCE_SUFFIXES = (
    "tests/test_smear.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
)


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


def _make_target(
    *,
    target_id: str,
    label: str,
    summary: str,
    confidence: str,
    status: str,
    task_type_hint: str | None,
) -> dict:
    return {
        "target_id": target_id,
        "label": label,
        "summary": summary,
        "confidence": confidence,
        "status": status,
        "task_type_hint": task_type_hint,
    }


def _pion_formula_proposals() -> tuple[list[dict], list[dict]]:
    citations = load_physics_citations(PION_CITATION_KEY)
    proposal = {
        "proposal_id": "pion_pseudoscalar_gamma5_twopt",
        "target_id": PION_TARGET_ID,
        "label": "Pion pseudoscalar two-point correlator",
        "operator": r"O_\pi(x) = \bar d(x) \gamma_5 u(x)",
        "correlator": r"C_\pi(t) = \sum_{\vec x} \langle O_\pi(\vec x,t) O_\pi^\dagger(\vec 0,0) \rangle",
        "convention": "Use the canonical pseudoscalar pion interpolating operator and the zero-momentum Euclidean two-point correlator.",
        "provenance": "local_references_plus_curated_citations",
        "local_references": list(PION_LOCAL_REFERENCE_SUFFIXES),
        "citations": citations,
    }
    return [proposal], citations


def _pion_dispersion_formula_proposals() -> tuple[list[dict], list[dict]]:
    citations = load_physics_citations(PION_DISPERSION_CITATION_KEY)
    proposal = {
        "proposal_id": "pion_dispersion_gamma5_momentum_projected_twopt",
        "target_id": PION_DISPERSION_TARGET_ID,
        "label": "Pion momentum-projected two-point correlator for dispersion analysis",
        "operator": r"O_\pi(x) = \bar d(x) \gamma_5 u(x)",
        "correlator": (
            r"C_\pi(t,\vec p) = \sum_{\vec x} e^{i\vec p\cdot\vec x}"
            r"\langle O_\pi(\vec x,t) O_\pi^\dagger(\vec 0,0) \rangle"
        ),
        "convention": (
            "Use the canonical pseudoscalar pion interpolating operator together with an explicit finite momentum list "
            "to build a narrow pion-dispersion workflow."
        ),
        "provenance": "local_references_plus_curated_citations" if citations else "local_references",
        "local_references": list(PION_DISPERSION_LOCAL_REFERENCE_SUFFIXES),
        "citations": citations,
    }
    return [proposal], citations


def _pion_pcac_formula_proposals() -> tuple[list[dict], list[dict]]:
    citations = load_physics_citations(PION_PCAC_CITATION_KEY)
    proposal = {
        "proposal_id": "pion_pcac_gamma5_gamma4_ratio",
        "target_id": PION_PCAC_TARGET_ID,
        "label": "Pion PCAC ratio from pseudoscalar and temporal-axial correlators",
        "operator": r"O_\pi(x) = \bar d(x)\gamma_5 u(x),\ A_4(x) = \bar d(x)\gamma_4\gamma_5 u(x)",
        "correlator": (
            r"C_{PP}(t)=\sum_{\vec x}\langle O_\pi(\vec x,t) O_\pi^\dagger(\vec 0,0)\rangle,\ "
            r"C_{A_4P}(t)=\sum_{\vec x}\langle A_4(\vec x,t) O_\pi^\dagger(\vec 0,0)\rangle"
        ),
        "convention": (
            "Follow the narrow local PyQUDA PCAC example: start from a gauge configuration, "
            "build wall-source propagators, contract zero-momentum pion and pionA4 channels, then form C_A4P / C_PP."
        ),
        "provenance": "local_references_plus_curated_citations" if citations else "local_references_plus_model_inference",
        "local_references": list(PION_PCAC_LOCAL_REFERENCE_SUFFIXES),
        "citations": citations,
    }
    return [proposal], citations


def _meson_spec_formula_proposals() -> tuple[list[dict], list[dict]]:
    citations = load_physics_citations(MESON_SPEC_CITATION_KEY)
    proposals = [
        {
            "proposal_id": "meson_spec_gamma5_wall_momentum_family",
            "target_id": MESON_SPEC_TARGET_ID,
            "label": "Meson spectroscopy correlator with pseudoscalar insertion",
            "operator": r"O_{\gamma_5}(x) = \bar q(x) \gamma_5 q(x)",
            "correlator": (
                r"C_{\gamma_5}(t,\vec p) = \sum_{\vec x} e^{i\vec p\cdot\vec x}"
                r"\langle O_{\gamma_5}(\vec x,t) O_{\gamma_5}^\dagger(\vec 0,0) \rangle"
            ),
            "convention": (
                "Use the fixed wall-source meson-spectroscopy path from the local PyQUDA meson-spec test, "
                "including the grounded momentum family with |p|^2 <= 9."
            ),
            "provenance": "local_references_plus_curated_citations" if citations else "local_references_plus_model_inference",
            "local_references": list(MESON_SPEC_LOCAL_REFERENCE_SUFFIXES),
            "citations": citations,
        },
        {
            "proposal_id": "meson_spec_gamma4gamma5_wall_momentum_family",
            "target_id": MESON_SPEC_TARGET_ID,
            "label": "Meson spectroscopy correlator with temporal-axial insertion",
            "operator": r"O_{\gamma_4\gamma_5}(x) = \bar q(x) \gamma_4 \gamma_5 q(x)",
            "correlator": (
                r"C_{\gamma_4\gamma_5}(t,\vec p) = \sum_{\vec x} e^{i\vec p\cdot\vec x}"
                r"\langle O_{\gamma_4\gamma_5}(\vec x,t) O_{\gamma_4\gamma_5}^\dagger(\vec 0,0) \rangle"
            ),
            "convention": (
                "Keep the same local meson-spec workflow, but expose the second fixed gamma-insertion channel "
                "already present in the upstream test path."
            ),
            "provenance": "local_references_plus_curated_citations" if citations else "local_references_plus_model_inference",
            "local_references": list(MESON_SPEC_LOCAL_REFERENCE_SUFFIXES),
            "citations": citations,
        },
    ]
    return proposals, citations


def _generic_meson_proposals() -> list[dict]:
    return [
        {
            "proposal_id": "meson_operator_needs_channel_choice",
            "target_id": MESON_UNSPECIFIED_TARGET_ID,
            "label": "Meson two-point correlator requires channel/operator choice",
            "operator": "Underspecified",
            "correlator": r"C(t) = \sum_{\vec x} \langle O(\vec x,t) O^\dagger(\vec 0,0) \rangle",
            "convention": "A meson two-point request is not runnable until the hadron channel and interpolating operator are fixed.",
            "provenance": "model_inference",
            "local_references": [],
            "citations": [],
        }
    ]


def _generic_baryon_proposals() -> list[dict]:
    return [
        {
            "proposal_id": "baryon_operator_needs_channel_choice",
            "target_id": BARYON_UNSPECIFIED_TARGET_ID,
            "label": "Baryon two-point correlator requires flavor/interpolator choice",
            "operator": "Underspecified",
            "correlator": r"C_B(t) = \sum_{\vec x} \langle O_B(\vec x,t) \bar O_B(\vec 0,0) \rangle",
            "convention": (
                "A nucleon/baryon two-point request is not runnable until the baryon channel and interpolating "
                "operator are fixed. The current grounded local baryon path is proton two-point only."
            ),
            "provenance": "model_inference",
            "local_references": [],
            "citations": [],
        }
    ]


def _generic_hadron_proposals() -> list[dict]:
    return [
        {
            "proposal_id": "hadron_operator_needs_channel_choice",
            "target_id": HADRON_UNSPECIFIED_TARGET_ID,
            "label": "Hadron two-point correlator requires hadron-channel choice",
            "operator": "Underspecified",
            "correlator": r"C_H(t) = \sum_{\vec x} \langle O_H(\vec x,t) O_H^\dagger(\vec 0,0) \rangle",
            "convention": (
                "A hadron-level request is not runnable until the channel is narrowed at least to meson versus baryon, "
                "and then to a grounded local operator family such as pion, rho/vector, meson spectrum, or proton."
            ),
            "provenance": "model_inference",
            "local_references": [],
            "citations": [],
        }
    ]


def _neutron_formula_proposals() -> list[dict]:
    return [
        {
            "proposal_id": "neutron_nucleon_gamma5_twopt",
            "target_id": NEUTRON_TARGET_ID,
            "label": "Neutron two-point correlator",
            "operator": r"N_\alpha^{(n)}(x) = \epsilon^{abc}(d^{aT}(x) C\gamma_5 u^b(x)) d^c_\alpha(x)",
            "correlator": r"C_n(t) = \sum_{\vec x} \langle N^{(n)}(\vec x,t) \bar N^{(n)}(\vec 0,0) \rangle",
            "convention": (
                "Treat neutron as the isospin partner of the proton nucleon two-point channel. "
                "This proposal is physics-side model inference only; the current grounded local workflow catalog "
                "does not implement a runnable neutron contraction path."
            ),
            "provenance": "model_inference",
            "local_references": [],
            "citations": [],
        }
    ]


def _quark_propagator_formula_proposals() -> tuple[list[dict], list[dict]]:
    proposal = {
        "proposal_id": "quark_propagator_point_source_clover",
        "target_id": QUARK_PROPAGATOR_TARGET_ID,
        "label": "Point-source quark propagator from a Clover solve",
        "operator": r"D[U]\, S(x; x_0) = \delta_{x,x_0}",
        "correlator": r"S(x; x_0) = D[U]^{-1}(x, x_0)",
        "convention": (
            "Follow the narrow local PyQUDA path: read a Chroma/QIO gauge, apply one stout-smear step, "
            "build a getDirac Clover operator with the local multigrid block shape, use a point source at "
            "[0, 0, 0, t_src], and save the resulting propagator as HDF5."
        ),
        "provenance": "local_references",
        "local_references": list(QUARK_PROPAGATOR_LOCAL_REFERENCE_SUFFIXES),
        "citations": [],
    }
    return [proposal], []


def _gaussian_shell_quark_propagator_formula_proposals() -> tuple[list[dict], list[dict]]:
    proposal = {
        "proposal_id": "quark_propagator_gaussian_shell_source_clover",
        "target_id": QUARK_PROPAGATOR_TARGET_ID,
        "label": "Gaussian-shell-source quark propagator from a Clover solve",
        "operator": r"D[U]\, S_{\mathrm{shell}}(x; x_0) = \phi_{\mathrm{gaussian}}(x; x_0,\rho,n_{\mathrm{steps}})",
        "correlator": r"S_{\mathrm{shell}}(x; x_0) = D[U]^{-1}\phi_{\mathrm{gaussian}}(x; x_0,\rho,n_{\mathrm{steps}})",
        "convention": (
            "Follow the narrow local PyQUDA Gaussian test path: read a Chroma/QIO gauge, build a point-source propagator "
            "at [0, 0, 0, t_src], apply source.gaussianSmear(..., rho=2.0, n_steps=5), invert with core.getClover + "
            "core.invertPropagator, and save the resulting propagator as HDF5."
        ),
        "provenance": "local_references",
        "local_references": list(QUARK_PROPAGATOR_GAUSSIAN_SHELL_LOCAL_REFERENCE_SUFFIXES),
        "citations": [],
    }
    return [proposal], []


def _ambiguous_quark_propagator_formula_proposals() -> tuple[list[dict], list[dict], list[str]]:
    point_proposals, _ = _quark_propagator_formula_proposals()
    gaussian_proposals, _ = _gaussian_shell_quark_propagator_formula_proposals()
    local_references = list(
        dict.fromkeys(
            list(QUARK_PROPAGATOR_LOCAL_REFERENCE_SUFFIXES)
            + list(QUARK_PROPAGATOR_GAUSSIAN_SHELL_LOCAL_REFERENCE_SUFFIXES)
        )
    )
    return point_proposals + gaussian_proposals, [], local_references


def _wilson_flow_formula_proposals() -> tuple[list[dict], list[dict]]:
    proposal = {
        "proposal_id": "wilson_flow_energy_density_history",
        "target_id": WILSON_FLOW_TARGET_ID,
        "label": "Wilson-flow energy-density history for a gauge field",
        "operator": r"\partial_t V_t(x,\mu) = - g_0^2 \{\partial_{x,\mu} S_G(V_t)\} V_t(x,\mu)",
        "correlator": r"E(t) \ \mathrm{sampled\ along\ the\ discrete\ Wilson-flow\ trajectory}",
        "convention": (
            "Follow the narrow local PyQUDA path: read a Chroma/QIO gauge, copy it, evolve it with "
            "wilsonFlowChroma(flow_steps, flow_epsilon), and save the returned energy-history array as npy."
        ),
        "provenance": "local_references_plus_model_inference",
        "local_references": list(WILSON_FLOW_LOCAL_REFERENCE_SUFFIXES),
        "citations": [],
    }
    return [proposal], []


def _stout_smear_formula_proposals() -> tuple[list[dict], list[dict]]:
    proposal = {
        "proposal_id": "stout_smear_one_step_rho0241_dirignore3",
        "target_id": STOUT_SMEAR_TARGET_ID,
        "label": "One-step stout-smeared gauge configuration",
        "operator": r"U_\mu(x) \rightarrow U_\mu^{\mathrm{stout}}(x; \rho=0.241,\ \mathrm{dir\_ignore}=3)",
        "correlator": "Gauge-field transformation only; no hadron correlator is formed in this workflow.",
        "convention": (
            "Follow the narrow local PyQUDA path: read a Chroma/QIO gauge, copy it, apply "
            "stoutSmear(1, 0.241, 3), and save the smeared gauge as npy."
        ),
        "provenance": "local_references_plus_model_inference",
        "local_references": list(STOUT_SMEAR_LOCAL_REFERENCE_SUFFIXES),
        "citations": [],
    }
    return [proposal], []


def _ape_smear_formula_proposals() -> tuple[list[dict], list[dict]]:
    proposal = {
        "proposal_id": "ape_smear_one_step_alpha25_dirignore4",
        "target_id": APE_SMEAR_TARGET_ID,
        "label": "One-step APE-smeared gauge configuration",
        "operator": r"U_\mu(x) \rightarrow U_\mu^{\mathrm{APE}}(x; \alpha=2.5,\ \mathrm{dir\_ignore}=4)",
        "correlator": "Gauge-field transformation only; no hadron correlator is formed in this workflow.",
        "convention": (
            "Follow the narrow local PyQUDA smear-test path: read a Chroma/QIO gauge, copy it, apply "
            "apeSmearChroma(1, 2.5, 4), and save the smeared gauge as npy."
        ),
        "provenance": "local_references_plus_model_inference",
        "local_references": list(APE_SMEAR_LOCAL_REFERENCE_SUFFIXES),
        "citations": [],
    }
    return [proposal], []


def _hyp_smear_formula_proposals() -> tuple[list[dict], list[dict]]:
    proposal = {
        "proposal_id": "hyp_smear_one_step_075_06_03_dirignore4",
        "target_id": HYP_SMEAR_TARGET_ID,
        "label": "One-step HYP-smeared gauge configuration",
        "operator": (
            r"U_\mu(x) \rightarrow U_\mu^{\mathrm{HYP}}"
            r"(x; \alpha_1=0.75,\ \alpha_2=0.6,\ \alpha_3=0.3,\ \mathrm{dir\_ignore}=4)"
        ),
        "correlator": "Gauge-field transformation only; no hadron correlator is formed in this workflow.",
        "convention": (
            "Follow the narrow local PyQUDA smear-test path: read a Chroma/QIO gauge, copy it, apply "
            "hypSmear(1, 0.75, 0.6, 0.3, 4), and save the smeared gauge as npy."
        ),
        "provenance": "local_references_plus_model_inference",
        "local_references": list(HYP_SMEAR_LOCAL_REFERENCE_SUFFIXES),
        "citations": [],
    }
    return [proposal], []


def _gauge_smear_family_proposals() -> tuple[list[dict], list[dict]]:
    stout, _ = _stout_smear_formula_proposals()
    ape, _ = _ape_smear_formula_proposals()
    hyp, _ = _hyp_smear_formula_proposals()
    return stout + ape + hyp, []


def _rho_vector_formula_proposals() -> tuple[list[dict], list[dict]]:
    proposal = {
        "proposal_id": "rho_vector_gammai_twopt",
        "target_id": RHO_TARGET_ID,
        "label": "Rho / vector meson two-point correlator",
        "operator": r"O_{\rho,i}(x) = \bar q(x) \gamma_i q(x)",
        "correlator": r"C_{\rho,ij}(t) = \sum_{\vec x} \langle O_{\rho,i}(\vec x,t) O_{\rho,j}^\dagger(\vec 0,0) \rangle",
        "convention": (
            "Use the current grounded rho/vector family only: gauge entry or existing propagator entry, the fixed spatial "
            "vector bilinear family gamma_1/gamma_2/gamma_3, zero momentum, and npy output. "
            "The gauge-entry branch performs the Clover inversion locally; the propagator-entry branch reuses stored wall-source propagators. "
            "The vector-channel operator choice is standard model inference; the contraction path is grounded in the "
            "local mesonspec test plus gamma helpers."
        ),
        "provenance": "local_references_plus_model_inference",
        "local_references": list(RHO_LOCAL_REFERENCE_SUFFIXES),
        "citations": [],
    }
    return [proposal], []


def _meson_spectrum_like_request(lowered: str) -> bool:
    return _contains_any(
        lowered,
        (
            "meson spectrum",
            "meson spectroscopy",
            "meson spect",
            "mesonspec",
            "gamma5 meson",
            "gamma4gamma5 meson",
            "gamma 4 gamma 5 meson",
        ),
    )


def _meson_correlator_like_request(lowered: str) -> bool:
    return "meson" in lowered and _contains_any(lowered, ("two-point", "two point", "2pt", "correlator"))


def _hadron_correlator_like_request(lowered: str) -> bool:
    return "hadron" in lowered and _contains_any(lowered, ("two-point", "two point", "2pt", "correlator", "script", "workflow"))


def _meson_side_request(lowered: str) -> bool:
    return _contains_any(
        lowered,
        (
            "meson",
            "pion",
            "pi meson",
            "meson spectrum",
            "meson spectroscopy",
            "mesonspec",
            "rho",
            "vector meson",
            "dispersion",
            "pcac",
        ),
    )


def _baryon_side_request(lowered: str) -> bool:
    return _contains_any(
        lowered,
        (
            "baryon",
            "nucleon",
            "proton",
            "neutron",
        ),
    )


def _mixed_hadron_request(lowered: str) -> bool:
    if not (_meson_side_request(lowered) and _baryon_side_request(lowered)):
        return False
    return _contains_any(
        lowered,
        (
            " or ",
            "either",
            "maybe",
            "not sure",
            "unsure",
            "which one",
            "not sure if",
        ),
    )


def _vector_meson_like_request(lowered: str) -> bool:
    if re.search(r"\brho\b", lowered):
        return True
    return _contains_any(
        lowered,
        (
            "vector meson",
            "vector-meson",
            "vector channel",
            "rho meson",
            "rho channel",
        ),
    )


def _meson_axial_operator_request(lowered: str) -> bool:
    if "meson" not in lowered:
        return False
    return _contains_any(
        lowered,
        (
            "axial meson",
            "axial-vector meson",
            "temporal axial meson",
            "gamma4gamma5 meson",
            "gamma4 gamma5 meson",
            "gamma 4 gamma 5 meson",
            "gamma4 gamma 5 meson",
        ),
    )


def _meson_pseudoscalar_operator_request(lowered: str) -> bool:
    if "meson" not in lowered:
        return False
    return _contains_any(
        lowered,
        (
            "pseudoscalar meson",
            "gamma5 meson",
            "gamma 5 meson",
            "gamma-5 meson",
        ),
    )


def _momentum_like_request(lowered: str) -> bool:
    if re.search(r"\bzero(?:-| )momentum\b", lowered) or re.search(r"\bzero mom\b", lowered):
        return False
    return _contains_any(
        lowered,
        (
            "momentum projection",
            "momentum projected",
            "momentum-projected",
            "nonzero momentum",
            "non-zero momentum",
            "dispersion",
            "finite momentum",
            "moving frame",
        ),
    )


def _unique_by_key(items: list[dict], key: str) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or value in seen:
            continue
        seen.add(value)
        unique.append(item)
    return unique


def _prioritize_formula_proposals(proposals: list[dict], target_priority: list[str]) -> list[dict]:
    ordered: list[dict] = []
    used_ids: set[str] = set()
    for target_id in target_priority:
        for item in proposals:
            if not isinstance(item, dict):
                continue
            proposal_id = item.get("proposal_id")
            if not isinstance(proposal_id, str) or proposal_id in used_ids:
                continue
            if item.get("target_id") != target_id:
                continue
            ordered.append(item)
            used_ids.add(proposal_id)
    for item in proposals:
        if not isinstance(item, dict):
            continue
        proposal_id = item.get("proposal_id")
        if not isinstance(proposal_id, str) or proposal_id in used_ids:
            continue
        ordered.append(item)
        used_ids.add(proposal_id)
    return ordered


def _ambiguous_meson_formula_proposals(lowered: str) -> tuple[list[dict], list[dict], list[str]]:
    pion_proposals, pion_citations = _pion_formula_proposals()
    dispersion_proposals, dispersion_citations = _pion_dispersion_formula_proposals()
    meson_spec_proposals, meson_spec_citations = _meson_spec_formula_proposals()
    combined_proposals = _generic_meson_proposals()
    if _vector_meson_like_request(lowered):
        rho_proposals, _rho_citations = _rho_vector_formula_proposals()
        combined_proposals.extend(rho_proposals)
    combined_proposals.extend(pion_proposals + dispersion_proposals + meson_spec_proposals)
    combined_citations = _unique_by_key(pion_citations + dispersion_citations + meson_spec_citations, "id")
    combined_references = list(
        dict.fromkeys(
            list(PION_LOCAL_REFERENCE_SUFFIXES)
            + list(PION_DISPERSION_LOCAL_REFERENCE_SUFFIXES)
            + list(MESON_SPEC_LOCAL_REFERENCE_SUFFIXES)
        )
    )
    return combined_proposals, combined_citations, combined_references


def _ambiguous_baryon_formula_proposals() -> tuple[list[dict], list[dict], list[str]]:
    proton_proposals, proton_citations = _proton_formula_proposals()
    combined_proposals = _generic_baryon_proposals() + proton_proposals + _neutron_formula_proposals()
    return combined_proposals, proton_citations, list(PROTON_LOCAL_REFERENCE_SUFFIXES)


def _ambiguous_hadron_formula_proposals(lowered: str) -> tuple[list[dict], list[dict], list[str]]:
    meson_proposals, meson_citations, meson_references = _ambiguous_meson_formula_proposals(lowered)
    baryon_proposals, baryon_citations, baryon_references = _ambiguous_baryon_formula_proposals()
    combined_proposals = _generic_hadron_proposals() + meson_proposals + baryon_proposals
    combined_citations = _unique_by_key(meson_citations + baryon_citations, "id")
    combined_references = list(dict.fromkeys(meson_references + baryon_references))
    return combined_proposals, combined_citations, combined_references


def _proton_formula_proposals() -> tuple[list[dict], list[dict]]:
    citations = load_physics_citations(PROTON_CITATION_KEY)
    proposal = {
        "proposal_id": "proton_nucleon_gamma5_twopt",
        "target_id": PROTON_TARGET_ID,
        "label": "Proton two-point correlator",
        "operator": r"N_\alpha(x) = \epsilon^{abc}(u^{aT}(x) C\gamma_5 d^b(x)) u^c_\alpha(x)",
        "correlator": r"C_N(t) = \sum_{\vec x} \langle N(\vec x,t) \bar N(\vec 0,0) \rangle",
        "convention": (
            "Use the standard local proton interpolating operator together with the parity-projected "
            "zero-momentum two-point contraction encoded in the local PyQUDA proton example."
        ),
        "provenance": "local_references_plus_curated_citations" if citations else "local_references_plus_model_inference",
        "local_references": list(PROTON_LOCAL_REFERENCE_SUFFIXES),
        "citations": citations,
    }
    return [proposal], citations


def _normalized_pion_request(lowered: str) -> bool:
    return bool(re.search(r"\bpion\b", lowered)) or "pi meson" in lowered or "π" in lowered


def _normalized_proton_request(lowered: str) -> bool:
    return bool(re.search(r"\bproton\b", lowered))


def _normalized_neutron_request(lowered: str) -> bool:
    return bool(re.search(r"\bneutron\b", lowered))


def _normalized_nucleon_request(lowered: str) -> bool:
    return bool(re.search(r"\bnucleon\b", lowered))


def _normalized_baryon_request(lowered: str) -> bool:
    return bool(re.search(r"\bbaryon\b", lowered))


def _expresses_uncertainty(lowered: str) -> bool:
    return _contains_any(
        lowered,
        (
            "not sure",
            "unsure",
            "uncertain",
            "don't know",
            "do not know",
            "which operator",
            "exact operator",
            "which gamma",
            "what gamma",
            "which insertion",
            "what insertion",
            "whether i need",
            "whether i want",
        ),
    )


def _explicit_pion_dispersion(lowered: str) -> bool:
    if not _normalized_pion_request(lowered):
        return False
    return _momentum_like_request(lowered) or _contains_any(lowered, ("multiple momenta",))


def _explicit_pion_pcac(lowered: str) -> bool:
    if "pcac" not in lowered:
        return False
    return _normalized_pion_request(lowered) or "a4" in lowered or "axial" in lowered


def _explicit_pion_twopt(lowered: str) -> bool:
    if not _normalized_pion_request(lowered):
        return False
    return _contains_any(
        lowered,
        (
            "pion two-point",
            "pion two point",
            "pion 2pt",
            "pion correlator",
            "pion two-point correlator",
            "pion 2-point",
            "pion 2 pt",
        ),
    )


def _explicit_neutron_twopt(lowered: str) -> bool:
    if not _normalized_neutron_request(lowered):
        return False
    return _contains_any(
        lowered,
        (
            "two-point",
            "two point",
            "2pt",
            "correlator",
        ),
    )


def _explicit_proton_twopt(lowered: str) -> bool:
    if not re.search(r"\bproton\b", lowered):
        return False
    return _contains_any(lowered, ("two-point", "two point", "2pt", "correlator"))


def _explicit_quark_propagator(lowered: str) -> bool:
    if _expresses_uncertainty(lowered):
        return False
    if "quark propagator" in lowered:
        return True
    return (
        "point-source propagator" in lowered
        or "point source propagator" in lowered
        or "shell-source propagator" in lowered
        or "shell source propagator" in lowered
        or "gaussian propagator" in lowered
        or ("generate propagator" in lowered and "quark" in lowered)
    )


def _explicit_gaussian_shell_quark_propagator(lowered: str) -> bool:
    if _expresses_uncertainty(lowered):
        return False
    if "propagator" not in lowered:
        return False
    return (
        "gaussian shell" in lowered
        or "gaussian-shell" in lowered
        or "gaussian smeared" in lowered
        or "gaussian-smeared" in lowered
        or "shell source" in lowered
        or "shell-source" in lowered
    )


def _hadron_or_channel_like_request(lowered: str) -> bool:
    return _contains_any(
        lowered,
        (
            "meson",
            "pion",
            "pi meson",
            "pcac",
            "dispersion",
            "rho",
            "vector meson",
            "proton",
            "neutron",
            "nucleon",
            "baryon",
            "hadron",
            "correlator",
            "two-point",
            "two point",
            "2pt",
        ),
    )


def _rough_propagator_request(lowered: str) -> bool:
    if "propagator" not in lowered:
        return False
    if (
        _explicit_wilson_flow(lowered)
        or _explicit_stout_smear(lowered)
        or _explicit_ape_smear(lowered)
        or _explicit_hyp_smear(lowered)
        or _rough_gauge_smear_request(lowered)
    ):
        return False
    if _hadron_or_channel_like_request(lowered):
        return False
    return _contains_any(
        lowered,
        (
            "generate",
            "write",
            "need",
            "want",
            "please",
            "example",
            "workflow",
            "script",
            "build",
            "make",
        ),
    )


def _explicit_wilson_flow(lowered: str) -> bool:
    return "wilson flow" in lowered or "gradient flow" in lowered


def _explicit_stout_smear(lowered: str) -> bool:
    return _contains_any(
        lowered,
        (
            "stout smear",
            "stout-smear",
            "stout smeared gauge",
            "stout-smeared gauge",
        ),
    )


def _explicit_ape_smear(lowered: str) -> bool:
    return _contains_any(
        lowered,
        (
            "ape smear",
            "ape-smear",
            "ape smeared gauge",
            "ape-smeared gauge",
        ),
    )


def _explicit_hyp_smear(lowered: str) -> bool:
    return _contains_any(
        lowered,
        (
            "hyp smear",
            "hyp-smear",
            "hyp smeared gauge",
            "hyp-smeared gauge",
        ),
    )


def _rough_gauge_smear_request(lowered: str) -> bool:
    if "gauge" not in lowered:
        return False
    if not _contains_any(lowered, ("smear", "smearing", "smooth", "smoothing")):
        return False
    if _contains_any(lowered, ("ape smear", "ape-smear", "hyp smear", "hyp-smear", "wilson flow", "gradient flow")):
        return False
    return True


def _explicit_rho_vector_meson(lowered: str) -> bool:
    if not _vector_meson_like_request(lowered):
        return False
    if _contains_any(lowered, ("not sure", "unsure", "exact operator", "which operator", "what operator")):
        return False
    return _contains_any(lowered, ("two-point", "two point", "2pt", "correlator", "script", "workflow"))


def _explicit_meson_spec(lowered: str) -> bool:
    if _expresses_uncertainty(lowered):
        return False
    if not _meson_spectrum_like_request(lowered):
        return False
    return _contains_any(
        lowered,
        (
            "meson spectrum",
            "meson spectroscopy",
            "mesonspec",
            "gamma5",
            "gamma 5",
            "gamma4gamma5",
            "gamma4 gamma5",
            "gamma 4 gamma 5",
            "spectroscopy correlator",
        ),
    )


def _ambiguous_meson_candidates(lowered: str) -> list[dict]:
    meson_summary = "The request asks for a meson correlator but does not identify the channel or operator."
    if _vector_meson_like_request(lowered):
        meson_summary = (
            "The request points to a rho/vector meson channel. The physics target is understandable, but the exact "
            "operator/source/momentum assumptions should still be confirmed before code generation."
        )
        rho_candidate = _make_target(
            target_id=RHO_TARGET_ID,
            label="rho / vector meson correlator",
            summary=(
                "Vector/rho wording identifies the standard vector-meson two-point target. The current first grounded "
                "family is narrow: wall source, local sink, spatial gamma_i channel, zero momentum, and gauge entry."
            ),
            confidence="medium",
            status="candidate",
            task_type_hint="rho_vector",
        )
        meson_spec_candidate = _make_target(
            target_id=MESON_SPEC_TARGET_ID,
            label="meson spectroscopy correlator",
            summary=(
                "A nearby grounded meson alternative is the fixed meson-spec workflow, but it covers the "
                "gamma5 / gamma4gamma5 insertion set rather than the vector gamma_i family."
            ),
            confidence="low",
            status="candidate",
            task_type_hint="meson_spec",
        )
        pion_candidate = _make_target(
            target_id=PION_TARGET_ID,
            label="pion two-point correlator",
            summary="If the vector wording was mistaken and the real target is the pseudoscalar pion channel, the narrow pion 2pt path is runnable.",
            confidence="low",
            status="candidate",
            task_type_hint="pion_2pt",
        )
        return [
            _make_target(
                target_id=MESON_UNSPECIFIED_TARGET_ID,
                label="meson correlator with unresolved channel/operator choice",
                summary=meson_summary,
                confidence="medium",
                status="needs_confirmation",
                task_type_hint=None,
            ),
            rho_candidate,
            meson_spec_candidate,
            pion_candidate,
        ]
    if _meson_spectrum_like_request(lowered):
        meson_spec_candidate = _make_target(
            target_id=MESON_SPEC_TARGET_ID,
            label="meson spectroscopy correlator",
            summary=(
                "Spectroscopy wording makes the grounded meson-spec workflow a plausible candidate, but the fixed "
                "gamma-insertion set and momentum-family assumptions still need confirmation."
            ),
            confidence="medium",
            status="candidate",
            task_type_hint="meson_spec",
        )
        pion_candidate = _make_target(
            target_id=PION_TARGET_ID,
            label="pion two-point correlator",
            summary="A simpler zero-momentum pion 2pt workflow is still plausible if spectroscopy language was informal.",
            confidence="low",
            status="candidate",
            task_type_hint="pion_2pt",
        )
        dispersion_candidate = _make_target(
            target_id=PION_DISPERSION_TARGET_ID,
            label="pion dispersion correlator",
            summary="If the intent is momentum-projected pion spectroscopy, the grounded dispersion workflow is another candidate.",
            confidence="low",
            status="candidate",
            task_type_hint="pion_dispersion",
        )
        return [
            _make_target(
                target_id=MESON_UNSPECIFIED_TARGET_ID,
                label="meson correlator with unresolved spectroscopy/operator choice",
                summary="The request suggests meson spectroscopy, but the exact grounded operator/channel choice still needs confirmation.",
                confidence="medium",
                status="needs_confirmation",
                task_type_hint=None,
            ),
            meson_spec_candidate,
            pion_candidate,
            dispersion_candidate,
        ]
    if _momentum_like_request(lowered):
        meson_summary = (
            "The request asks for a meson correlator with momentum-like language, but the hadron channel/operator "
            "still needs confirmation before it can map to a supported workflow."
        )
        dispersion_candidate = _make_target(
            target_id=PION_DISPERSION_TARGET_ID,
            label="pion dispersion correlator",
            summary="Momentum/dispersive wording makes the supported pion-dispersion workflow the strongest runnable candidate.",
            confidence="medium",
            status="candidate",
            task_type_hint="pion_dispersion",
        )
        pion_candidate = _make_target(
            target_id=PION_TARGET_ID,
            label="pion two-point correlator",
            summary="A zero-momentum pion two-point workflow is still plausible if the momentum wording was informal.",
            confidence="low",
            status="candidate",
            task_type_hint="pion_2pt",
        )
        return [
            _make_target(
                target_id=MESON_UNSPECIFIED_TARGET_ID,
                label="meson two-point correlator with unspecified channel/operator",
                summary=meson_summary,
                confidence="medium",
                status="needs_confirmation",
                task_type_hint=None,
            ),
            dispersion_candidate,
            pion_candidate,
        ]

    if _meson_axial_operator_request(lowered):
        meson_summary = (
            "The request asks for an axial/gamma4gamma5 meson correlator. The strongest grounded local candidate "
            "is the meson-spectrum workflow with the fixed temporal-axial insertion, but the channel and fixed "
            "momentum-family assumptions still need confirmation."
        )
        meson_spec_candidate = _make_target(
            target_id=MESON_SPEC_TARGET_ID,
            label="meson spectroscopy correlator",
            summary=(
                "Axial/gamma4gamma5 wording points most directly to the grounded meson-spec workflow, which already "
                "contains the temporal-axial insertion family."
            ),
            confidence="medium",
            status="candidate",
            task_type_hint="meson_spec",
        )
        pion_candidate = _make_target(
            target_id=PION_TARGET_ID,
            label="pion two-point correlator",
            summary=(
                "A plain pion two-point workflow is less likely here because the request specifies an axial meson "
                "operator rather than the default pseudoscalar pion channel."
            ),
            confidence="low",
            status="candidate",
            task_type_hint="pion_2pt",
        )
        return [
            _make_target(
                target_id=MESON_UNSPECIFIED_TARGET_ID,
                label="meson correlator with unresolved axial/channel choice",
                summary=meson_summary,
                confidence="medium",
                status="needs_confirmation",
                task_type_hint=None,
            ),
            meson_spec_candidate,
            pion_candidate,
        ]

    if _meson_pseudoscalar_operator_request(lowered):
        meson_summary = (
            "The request asks for a pseudoscalar/gamma5 meson correlator. The strongest narrow local candidate is "
            "the pion pseudoscalar two-point path, but the meson channel still needs confirmation."
        )
        pion_candidate = _make_target(
            target_id=PION_TARGET_ID,
            label="pion two-point correlator",
            summary=(
                "Pseudoscalar meson wording aligns most naturally with the grounded pion gamma5 two-point workflow."
            ),
            confidence="medium",
            status="candidate",
            task_type_hint="pion_2pt",
        )
        meson_spec_candidate = _make_target(
            target_id=MESON_SPEC_TARGET_ID,
            label="meson spectroscopy correlator",
            summary=(
                "If the intent is a broader meson-spectroscopy path with the fixed gamma5 insertion family and "
                "momentum set, the grounded meson-spec workflow is another candidate."
            ),
            confidence="low",
            status="candidate",
            task_type_hint="meson_spec",
        )
        return [
            _make_target(
                target_id=MESON_UNSPECIFIED_TARGET_ID,
                label="meson correlator with unresolved pseudoscalar/channel choice",
                summary=meson_summary,
                confidence="medium",
                status="needs_confirmation",
                task_type_hint=None,
            ),
            pion_candidate,
            meson_spec_candidate,
        ]

    pion_candidate = _make_target(
        target_id=PION_TARGET_ID,
        label="pion two-point correlator",
        summary="Pion is the most likely meson channel for the current grounded workflows, but it is not confirmed by the request.",
        confidence="low",
        status="candidate",
        task_type_hint="pion_2pt",
    )
    dispersion_candidate = _make_target(
        target_id=PION_DISPERSION_TARGET_ID,
        label="pion dispersion correlator",
        summary="If the user actually intends a momentum-projected pion study, the supported narrow dispersion workflow is another plausible candidate.",
        confidence="low",
        status="candidate",
        task_type_hint="pion_dispersion",
    )
    meson_spec_candidate = _make_target(
        target_id=MESON_SPEC_TARGET_ID,
        label="meson spectroscopy correlator",
        summary="If the intent is a small meson-spectroscopy code path with fixed gamma insertions, the grounded meson-spec workflow is another plausible candidate.",
        confidence="low",
        status="candidate",
        task_type_hint="meson_spec",
    )
    return [
        _make_target(
            target_id=MESON_UNSPECIFIED_TARGET_ID,
            label="meson two-point correlator with unspecified channel/operator",
            summary=meson_summary,
            confidence="medium",
            status="needs_confirmation",
            task_type_hint=None,
        ),
        pion_candidate,
        meson_spec_candidate,
        dispersion_candidate,
    ]


def _ambiguous_baryon_candidates(lowered: str) -> list[dict]:
    if _normalized_nucleon_request(lowered):
        unresolved_summary = (
            "The request asks for a nucleon correlator, but nucleon-level wording still leaves the baryon channel "
            "and implementation target unresolved. The current grounded local baryon path is proton two-point only; "
            "neutron remains a physics-side candidate but is not implemented as a runnable local workflow."
        )
    else:
        unresolved_summary = (
            "The request asks for a baryon correlator, but the baryon channel is not specific enough to map directly "
            "to a supported implementation. The current grounded local baryon path is proton two-point only; "
            "neutron remains a physics-side candidate but is not implemented as a runnable local workflow."
        )
    proton_candidate = _make_target(
        target_id=PROTON_TARGET_ID,
        label="proton two-point correlator",
        summary=(
            "Proton is the only currently grounded baryon workflow family in local PyQUDA references, but that "
            "channel still needs explicit confirmation."
        ),
        confidence="medium",
        status="candidate",
        task_type_hint="proton_2pt",
    )
    neutron_candidate = _make_target(
        target_id=NEUTRON_TARGET_ID,
        label="neutron two-point correlator",
        summary=(
            "Neutron is a standard nucleon-channel candidate at the physics level, but the current grounded local "
            "workflow catalog does not implement a runnable neutron path yet."
        ),
        confidence="medium",
        status="candidate",
        task_type_hint=None,
    )
    return [
        _make_target(
            target_id=BARYON_UNSPECIFIED_TARGET_ID,
            label="baryon two-point correlator with unresolved channel/operator",
            summary=unresolved_summary,
            confidence="medium",
            status="needs_confirmation",
            task_type_hint=None,
        ),
        proton_candidate,
        neutron_candidate,
    ]


def _ambiguous_hadron_candidates() -> list[dict]:
    meson_candidate = _make_target(
        target_id=MESON_UNSPECIFIED_TARGET_ID,
        label="meson correlator with unresolved channel/operator choice",
        summary=(
            "One grounded branch family starts on the meson side: the current local catalog can narrow this to pion, "
            "pion dispersion, meson spectrum, or rho/vector after one more physics confirmation step."
        ),
        confidence="medium",
        status="candidate",
        task_type_hint=None,
    )
    baryon_candidate = _make_target(
        target_id=BARYON_UNSPECIFIED_TARGET_ID,
        label="baryon correlator with unresolved channel/operator choice",
        summary=(
            "The other grounded branch family starts on the baryon side: the current local catalog can narrow this to "
            "proton now, while neutron remains physics-side only and is still explicit unsupported."
        ),
        confidence="medium",
        status="candidate",
        task_type_hint=None,
    )
    pion_candidate = _make_target(
        target_id=PION_TARGET_ID,
        label="pion two-point correlator",
        summary="If the rough hadron request was really aiming at the simplest supported meson channel, the zero-momentum pion path is the narrowest grounded candidate.",
        confidence="low",
        status="candidate",
        task_type_hint="pion_2pt",
    )
    proton_candidate = _make_target(
        target_id=PROTON_TARGET_ID,
        label="proton two-point correlator",
        summary="If the rough hadron request was really aiming at the grounded baryon side, proton is the currently runnable local candidate.",
        confidence="low",
        status="candidate",
        task_type_hint="proton_2pt",
    )
    return [
        _make_target(
            target_id=HADRON_UNSPECIFIED_TARGET_ID,
            label="hadron correlator with unresolved meson/baryon channel choice",
            summary="The request only fixes a generic hadron correlator; it still needs at least meson versus baryon confirmation before workflow matching can be honest.",
            confidence="medium",
            status="needs_confirmation",
            task_type_hint=None,
        ),
        meson_candidate,
        baryon_candidate,
        pion_candidate,
        proton_candidate,
    ]


def _ambiguous_cross_hadron_candidates(lowered: str) -> list[dict]:
    if _meson_spectrum_like_request(lowered):
        meson_candidate = _make_target(
            target_id=MESON_SPEC_TARGET_ID,
            label="meson spectroscopy correlator",
            summary="The meson-side wording points most directly to the grounded meson-spectrum family with the fixed gamma5 / gamma4gamma5 insertion set.",
            confidence="medium",
            status="candidate",
            task_type_hint="meson_spec",
        )
    elif _vector_meson_like_request(lowered):
        meson_candidate = _make_target(
            target_id=RHO_TARGET_ID,
            label="rho / vector meson correlator",
            summary="The meson-side wording points most directly to the grounded rho/vector family with the fixed spatial gamma_i channel.",
            confidence="medium",
            status="candidate",
            task_type_hint="rho_vector",
        )
    elif _explicit_pion_dispersion(lowered) or _momentum_like_request(lowered):
        meson_candidate = _make_target(
            target_id=PION_DISPERSION_TARGET_ID,
            label="pion dispersion correlator",
            summary="The meson-side wording points most directly to the grounded momentum-projected pion-dispersion family.",
            confidence="medium",
            status="candidate",
            task_type_hint="pion_dispersion",
        )
    elif _normalized_pion_request(lowered):
        meson_candidate = _make_target(
            target_id=PION_TARGET_ID,
            label="pion two-point correlator",
            summary="The meson-side wording points most directly to the grounded zero-momentum pion two-point family.",
            confidence="medium",
            status="candidate",
            task_type_hint="pion_2pt",
        )
    else:
        meson_candidate = _make_target(
            target_id=MESON_UNSPECIFIED_TARGET_ID,
            label="meson correlator with unresolved channel/operator choice",
            summary="The meson-side branch is still unresolved and needs one more channel/operator confirmation before workflow matching can be honest.",
            confidence="medium",
            status="candidate",
            task_type_hint=None,
        )

    if _normalized_neutron_request(lowered):
        baryon_candidate = _make_target(
            target_id=NEUTRON_TARGET_ID,
            label="neutron two-point correlator",
            summary="The baryon-side wording points to neutron, but that path remains explicit unsupported in the current grounded local workflow catalog.",
            confidence="medium",
            status="candidate",
            task_type_hint=None,
        )
    elif _normalized_proton_request(lowered):
        baryon_candidate = _make_target(
            target_id=PROTON_TARGET_ID,
            label="proton two-point correlator",
            summary="The baryon-side wording points most directly to the grounded proton two-point family.",
            confidence="medium",
            status="candidate",
            task_type_hint="proton_2pt",
        )
    else:
        baryon_candidate = _make_target(
            target_id=BARYON_UNSPECIFIED_TARGET_ID,
            label="baryon correlator with unresolved channel/operator choice",
            summary="The baryon-side branch is still unresolved and needs one more channel confirmation before workflow matching can be honest.",
            confidence="medium",
            status="candidate",
            task_type_hint=None,
        )

    return [
        _make_target(
            target_id=HADRON_UNSPECIFIED_TARGET_ID,
            label="hadron correlator with unresolved meson/baryon branch choice",
            summary="The request presents multiple hadron-channel families at once, so the system must keep the physics target above both branches until the user confirms which side is intended.",
            confidence="medium",
            status="needs_confirmation",
            task_type_hint=None,
        ),
        meson_candidate,
        baryon_candidate,
    ]


def interpret_request(user_request: str) -> PhysicsTargetArtifact:
    lowered = user_request.lower()
    physics = PhysicsTargetArtifact(user_request=user_request.strip())

    if _mixed_hadron_request(lowered):
        proposals, citations, local_references = _ambiguous_hadron_formula_proposals(lowered)
        candidates = _ambiguous_cross_hadron_candidates(lowered)
        physics.status = "needs_confirmation"
        physics.candidate_targets = candidates
        physics.inferred_interpretation = physics.candidate_targets[0]
        physics.formula_proposals = _prioritize_formula_proposals(
            proposals,
            [
                HADRON_UNSPECIFIED_TARGET_ID,
                *[item.get("target_id") for item in candidates if isinstance(item.get("target_id"), str)],
            ],
        )
        physics.local_references = local_references
        physics.external_citations = citations
        physics.inferred_fields["target_id"] = HADRON_UNSPECIFIED_TARGET_ID
        return physics

    if _explicit_pion_dispersion(lowered):
        candidate = _make_target(
            target_id=PION_DISPERSION_TARGET_ID,
            label="pion dispersion correlator",
            summary="User explicitly asked for a pion momentum-projected correlator / dispersion workflow.",
            confidence="high",
            status="confirmed",
            task_type_hint="pion_dispersion",
        )
        proposals, citations = _pion_dispersion_formula_proposals()
        physics.status = "confirmed"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.confirmed_interpretation = candidate
        physics.task_type_hint = "pion_dispersion"
        physics.formula_proposals = proposals
        physics.local_references = list(PION_DISPERSION_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.user_confirmed_fields["target_id"] = PION_DISPERSION_TARGET_ID
        return physics

    if _explicit_pion_pcac(lowered):
        candidate = _make_target(
            target_id=PION_PCAC_TARGET_ID,
            label="pion pcac ratio correlator",
            summary="User explicitly asked for the narrow pion PCAC ratio path grounded in the local PyQUDA example.",
            confidence="high",
            status="confirmed",
            task_type_hint="pion_pcac",
        )
        proposals, citations = _pion_pcac_formula_proposals()
        physics.status = "confirmed"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.confirmed_interpretation = candidate
        physics.task_type_hint = "pion_pcac"
        physics.formula_proposals = proposals
        physics.local_references = list(PION_PCAC_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.user_confirmed_fields["target_id"] = PION_PCAC_TARGET_ID
        return physics

    if _explicit_pion_twopt(lowered):
        candidate = _make_target(
            target_id=PION_TARGET_ID,
            label="pion two-point correlator",
            summary="User explicitly asked for a pion two-point correlator.",
            confidence="high",
            status="confirmed",
            task_type_hint="pion_2pt",
        )
        proposals, citations = _pion_formula_proposals()
        physics.status = "confirmed"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.confirmed_interpretation = candidate
        physics.task_type_hint = "pion_2pt"
        physics.formula_proposals = proposals
        physics.local_references = list(PION_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.user_confirmed_fields["target_id"] = PION_TARGET_ID
        return physics

    if _explicit_meson_spec(lowered):
        candidate = _make_target(
            target_id=MESON_SPEC_TARGET_ID,
            label="meson spectroscopy correlator",
            summary="User explicitly asked for the grounded meson-spectroscopy correlator path with fixed gamma insertions.",
            confidence="high",
            status="confirmed",
            task_type_hint="meson_spec",
        )
        proposals, citations = _meson_spec_formula_proposals()
        physics.status = "confirmed"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.confirmed_interpretation = candidate
        physics.task_type_hint = "meson_spec"
        physics.formula_proposals = proposals
        physics.local_references = list(MESON_SPEC_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.user_confirmed_fields["target_id"] = MESON_SPEC_TARGET_ID
        return physics

    if _explicit_rho_vector_meson(lowered):
        candidate = _make_target(
            target_id=RHO_TARGET_ID,
            label="rho / vector meson correlator",
            summary=(
                "User explicitly asked for a rho/vector meson correlator. The first supported family is the narrow "
                "gauge-entry wall-source zero-momentum vector-channel path."
            ),
            confidence="high",
            status="confirmed",
            task_type_hint="rho_vector",
        )
        proposals, citations = _rho_vector_formula_proposals()
        physics.status = "confirmed"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.confirmed_interpretation = candidate
        physics.formula_proposals = proposals
        physics.local_references = list(RHO_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.user_confirmed_fields["target_id"] = RHO_TARGET_ID
        physics.task_type_hint = "rho_vector"
        return physics

    if _explicit_gaussian_shell_quark_propagator(lowered):
        candidate = _make_target(
            target_id=QUARK_PROPAGATOR_TARGET_ID,
            label="quark propagator",
            summary="User explicitly asked for a grounded Gaussian-shell-source quark-propagator generation path.",
            confidence="high",
            status="confirmed",
            task_type_hint="quark_propagator",
        )
        proposals, citations = _gaussian_shell_quark_propagator_formula_proposals()
        physics.status = "confirmed"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.confirmed_interpretation = candidate
        physics.task_type_hint = "quark_propagator"
        physics.formula_proposals = proposals
        physics.local_references = list(QUARK_PROPAGATOR_GAUSSIAN_SHELL_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.user_confirmed_fields["target_id"] = QUARK_PROPAGATOR_TARGET_ID
        physics.inferred_fields["source_smearing_kind"] = "gaussian_shell"
        return physics

    if _explicit_quark_propagator(lowered):
        candidate = _make_target(
            target_id=QUARK_PROPAGATOR_TARGET_ID,
            label="quark propagator",
            summary="User explicitly asked for a grounded quark-propagator generation path.",
            confidence="high",
            status="confirmed",
            task_type_hint="quark_propagator",
        )
        proposals, citations = _quark_propagator_formula_proposals()
        physics.status = "confirmed"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.confirmed_interpretation = candidate
        physics.task_type_hint = "quark_propagator"
        physics.formula_proposals = proposals
        physics.local_references = list(QUARK_PROPAGATOR_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.user_confirmed_fields["target_id"] = QUARK_PROPAGATOR_TARGET_ID
        return physics

    if _rough_propagator_request(lowered):
        candidate = _make_target(
            target_id=QUARK_PROPAGATOR_TARGET_ID,
            label="quark propagator",
            summary=(
                "The request asks for a propagator-generation script, but the grounded local implementation branch "
                "still needs confirmation: point-source Clover propagator or Gaussian-shell-source Clover propagator."
            ),
            confidence="medium",
            status="needs_confirmation",
            task_type_hint="quark_propagator",
        )
        proposals, citations, local_references = _ambiguous_quark_propagator_formula_proposals()
        physics.status = "needs_confirmation"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.task_type_hint = "quark_propagator"
        physics.formula_proposals = proposals
        physics.local_references = local_references
        physics.external_citations = citations
        physics.inferred_fields["target_id"] = QUARK_PROPAGATOR_TARGET_ID
        return physics

    if _explicit_wilson_flow(lowered):
        candidate = _make_target(
            target_id=WILSON_FLOW_TARGET_ID,
            label="wilson-flow energy observable",
            summary="User explicitly asked for a Wilson-flow / gradient-flow gauge evolution path.",
            confidence="high",
            status="confirmed",
            task_type_hint="wilson_flow",
        )
        proposals, citations = _wilson_flow_formula_proposals()
        physics.status = "confirmed"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.confirmed_interpretation = candidate
        physics.task_type_hint = "wilson_flow"
        physics.formula_proposals = proposals
        physics.local_references = list(WILSON_FLOW_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.user_confirmed_fields["target_id"] = WILSON_FLOW_TARGET_ID
        return physics

    if _explicit_ape_smear(lowered):
        candidate = _make_target(
            target_id=APE_SMEAR_TARGET_ID,
            label="APE-smeared gauge configuration",
            summary="User explicitly asked for the narrow local APE-smear gauge-output path.",
            confidence="high",
            status="confirmed",
            task_type_hint="ape_smear",
        )
        proposals, citations = _ape_smear_formula_proposals()
        physics.status = "confirmed"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.confirmed_interpretation = candidate
        physics.task_type_hint = "ape_smear"
        physics.formula_proposals = proposals
        physics.local_references = list(APE_SMEAR_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.user_confirmed_fields["target_id"] = APE_SMEAR_TARGET_ID
        return physics

    if _explicit_hyp_smear(lowered):
        candidate = _make_target(
            target_id=HYP_SMEAR_TARGET_ID,
            label="HYP-smeared gauge configuration",
            summary="User explicitly asked for the narrow local HYP-smear gauge-output path.",
            confidence="high",
            status="confirmed",
            task_type_hint="hyp_smear",
        )
        proposals, citations = _hyp_smear_formula_proposals()
        physics.status = "confirmed"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.confirmed_interpretation = candidate
        physics.task_type_hint = "hyp_smear"
        physics.formula_proposals = proposals
        physics.local_references = list(HYP_SMEAR_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.user_confirmed_fields["target_id"] = HYP_SMEAR_TARGET_ID
        return physics

    if _explicit_stout_smear(lowered):
        candidate = _make_target(
            target_id=STOUT_SMEAR_TARGET_ID,
            label="stout-smeared gauge configuration",
            summary="User explicitly asked for the narrow local stout-smear gauge-output path.",
            confidence="high",
            status="confirmed",
            task_type_hint="stout_smear",
        )
        proposals, citations = _stout_smear_formula_proposals()
        physics.status = "confirmed"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.confirmed_interpretation = candidate
        physics.task_type_hint = "stout_smear"
        physics.formula_proposals = proposals
        physics.local_references = list(STOUT_SMEAR_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.user_confirmed_fields["target_id"] = STOUT_SMEAR_TARGET_ID
        return physics

    if _normalized_pion_request(lowered):
        if "pcac" in lowered or "a4" in lowered or "axial" in lowered:
            candidate = _make_target(
                target_id=PION_PCAC_TARGET_ID,
                label="pion pcac ratio correlator",
                summary="The request likely refers to the local pion PCAC ratio path, but the PCAC interpretation is still inferred from rough wording.",
                confidence="medium",
                status="inferred",
                task_type_hint="pion_pcac",
            )
            pion_candidate = _make_target(
                target_id=PION_TARGET_ID,
                label="pion two-point correlator",
                summary="A plain zero-momentum pion two-point workflow is another plausible interpretation if the PCAC wording was informal.",
                confidence="low",
                status="candidate",
                task_type_hint="pion_2pt",
            )
            proposals, citations = _pion_pcac_formula_proposals()
            physics.status = "needs_confirmation"
            physics.candidate_targets = [candidate, pion_candidate]
            physics.inferred_interpretation = candidate
            physics.task_type_hint = "pion_pcac"
            physics.formula_proposals = proposals
            physics.local_references = list(PION_PCAC_LOCAL_REFERENCE_SUFFIXES)
            physics.external_citations = citations
            physics.inferred_fields["target_id"] = PION_PCAC_TARGET_ID
            return physics
        if _contains_any(lowered, ("momentum", "dispersion")):
            dispersion_candidate = _make_target(
                target_id=PION_DISPERSION_TARGET_ID,
                label="pion dispersion correlator",
                summary="The request likely refers to a pion momentum-projected correlator, but the exact supported workflow still needs confirmation.",
                confidence="medium",
                status="inferred",
                task_type_hint="pion_dispersion",
            )
            pion_candidate = _make_target(
                target_id=PION_TARGET_ID,
                label="pion two-point correlator",
                summary="A zero-momentum pion two-point workflow is another plausible interpretation of the rough request.",
                confidence="low",
                status="candidate",
                task_type_hint="pion_2pt",
            )
            proposals, citations = _pion_dispersion_formula_proposals()
            physics.status = "needs_confirmation"
            physics.candidate_targets = [dispersion_candidate, pion_candidate]
            physics.inferred_interpretation = dispersion_candidate
            physics.task_type_hint = "pion_dispersion"
            physics.formula_proposals = proposals
            physics.local_references = list(PION_DISPERSION_LOCAL_REFERENCE_SUFFIXES)
            physics.external_citations = citations
            physics.inferred_fields["target_id"] = PION_DISPERSION_TARGET_ID
            return physics

        candidate = _make_target(
            target_id=PION_TARGET_ID,
            label="pion two-point correlator",
            summary="The request likely refers to a pion two-point correlator, but the normalized physics label is inferred from the rough wording.",
            confidence="medium",
            status="inferred",
            task_type_hint="pion_2pt",
        )
        proposals, citations = _pion_formula_proposals()
        physics.status = "needs_confirmation"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.task_type_hint = "pion_2pt"
        physics.formula_proposals = proposals
        physics.local_references = list(PION_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.inferred_fields["target_id"] = PION_TARGET_ID
        return physics

    if (
        "gauge flow" in lowered
        or "flowed gauge" in lowered
        or ("flow history" in lowered and "gauge" in lowered)
    ):
        candidate = _make_target(
            target_id=WILSON_FLOW_TARGET_ID,
            label="wilson-flow energy observable",
            summary="The request likely refers to a Wilson-flow / gradient-flow gauge evolution path, but the flow interpretation is still inferred from rough wording.",
            confidence="medium",
            status="inferred",
            task_type_hint="wilson_flow",
        )
        proposals, citations = _wilson_flow_formula_proposals()
        physics.status = "needs_confirmation"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.task_type_hint = "wilson_flow"
        physics.formula_proposals = proposals
        physics.local_references = list(WILSON_FLOW_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.inferred_fields["target_id"] = WILSON_FLOW_TARGET_ID
        return physics

    if _rough_gauge_smear_request(lowered):
        stout_candidate = _make_target(
            target_id=STOUT_SMEAR_TARGET_ID,
            label="stout-smeared gauge configuration",
            summary=(
                "The request likely refers to the narrow local stout-smear gauge-output path, but the exact "
                "smearing family is still inferred from rough wording and the local smear test also demonstrates "
                "APE and HYP variants."
            ),
            confidence="medium",
            status="inferred",
            task_type_hint="stout_smear",
        )
        ape_candidate = _make_target(
            target_id=APE_SMEAR_TARGET_ID,
            label="APE-smeared gauge configuration",
            summary="The local smear test also contains a narrow APE-smear path via apeSmearChroma(1, 2.5, 4).",
            confidence="low",
            status="candidate",
            task_type_hint="ape_smear",
        )
        hyp_candidate = _make_target(
            target_id=HYP_SMEAR_TARGET_ID,
            label="HYP-smeared gauge configuration",
            summary=(
                "The local smear test also contains a narrow HYP-smear path via "
                "hypSmear(1, 0.75, 0.6, 0.3, 4), and this repository now exposes it as a separate runnable family."
            ),
            confidence="low",
            status="candidate",
            task_type_hint="hyp_smear",
        )
        proposals, citations = _gauge_smear_family_proposals()
        physics.status = "needs_confirmation"
        physics.candidate_targets = [stout_candidate, ape_candidate, hyp_candidate]
        physics.inferred_interpretation = stout_candidate
        physics.task_type_hint = "stout_smear"
        physics.formula_proposals = proposals
        physics.local_references = list(STOUT_SMEAR_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.inferred_fields["target_id"] = STOUT_SMEAR_TARGET_ID
        return physics

    if _explicit_proton_twopt(lowered):
        candidate = _make_target(
            target_id=PROTON_TARGET_ID,
            label="proton two-point correlator",
            summary="User explicitly asked for a proton two-point correlator.",
            confidence="high",
            status="confirmed",
            task_type_hint="proton_2pt",
        )
        proposals, citations = _proton_formula_proposals()
        physics.status = "confirmed"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.confirmed_interpretation = candidate
        physics.task_type_hint = "proton_2pt"
        physics.formula_proposals = proposals
        physics.local_references = list(PROTON_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.user_confirmed_fields["target_id"] = PROTON_TARGET_ID
        return physics

    if _explicit_neutron_twopt(lowered):
        candidate = _make_target(
            target_id=NEUTRON_TARGET_ID,
            label="neutron two-point correlator",
            summary=(
                "User explicitly asked for a neutron two-point correlator. The physics target is clear, but the "
                "current grounded local PyQUDA workflow catalog does not implement a runnable neutron path."
            ),
            confidence="high",
            status="confirmed",
            task_type_hint=None,
        )
        reason = (
            "Neutron two-point correlators are not implemented in the current grounded local workflow catalog. "
            "Nearest grounded baryon alternative is proton two-point."
        )
        physics.status = "confirmed"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.confirmed_interpretation = candidate
        physics.task_type_hint = None
        physics.formula_proposals = _neutron_formula_proposals()
        physics.local_references = []
        physics.external_citations = []
        physics.user_confirmed_fields["target_id"] = NEUTRON_TARGET_ID
        physics.unsupported_fields["target_id"] = reason
        physics.unsupported_reasons.append(reason)
        return physics

    if _normalized_proton_request(lowered):
        candidate = _make_target(
            target_id=PROTON_TARGET_ID,
            label="proton two-point correlator",
            summary="The request likely refers to a proton two-point correlator, but the normalized hadron target is inferred from rough wording.",
            confidence="medium",
            status="inferred",
            task_type_hint="proton_2pt",
        )
        proposals, citations = _proton_formula_proposals()
        physics.status = "needs_confirmation"
        physics.candidate_targets = [candidate]
        physics.inferred_interpretation = candidate
        physics.task_type_hint = "proton_2pt"
        physics.formula_proposals = proposals
        physics.local_references = list(PROTON_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.inferred_fields["target_id"] = PROTON_TARGET_ID
        return physics

    if _normalized_nucleon_request(lowered) or (
        _normalized_baryon_request(lowered) and _contains_any(lowered, ("two-point", "two point", "2pt", "correlator"))
    ):
        proposals, citations, local_references = _ambiguous_baryon_formula_proposals()
        physics.status = "needs_confirmation"
        physics.candidate_targets = _ambiguous_baryon_candidates(lowered)
        physics.inferred_interpretation = physics.candidate_targets[0]
        physics.formula_proposals = proposals
        physics.local_references = local_references
        physics.external_citations = citations
        physics.inferred_fields["target_id"] = BARYON_UNSPECIFIED_TARGET_ID
        return physics

    if _hadron_correlator_like_request(lowered):
        proposals, citations, local_references = _ambiguous_hadron_formula_proposals(lowered)
        candidates = _ambiguous_hadron_candidates()
        physics.status = "needs_confirmation"
        physics.candidate_targets = candidates
        physics.inferred_interpretation = physics.candidate_targets[0]
        physics.formula_proposals = _prioritize_formula_proposals(
            proposals,
            [
                HADRON_UNSPECIFIED_TARGET_ID,
                MESON_UNSPECIFIED_TARGET_ID,
                BARYON_UNSPECIFIED_TARGET_ID,
                *[item.get("target_id") for item in candidates if isinstance(item.get("target_id"), str)],
            ],
        )
        physics.local_references = local_references
        physics.external_citations = citations
        physics.inferred_fields["target_id"] = HADRON_UNSPECIFIED_TARGET_ID
        return physics

    if _meson_spectrum_like_request(lowered):
        candidate = _make_target(
            target_id=MESON_SPEC_TARGET_ID,
            label="meson spectroscopy correlator",
            summary=(
                "The request likely refers to the grounded meson-spectroscopy path with fixed gamma insertions and a "
                "validated momentum family, but that interpretation still needs confirmation."
            ),
            confidence="medium",
            status="inferred",
            task_type_hint="meson_spec",
        )
        pion_candidate = _make_target(
            target_id=PION_TARGET_ID,
            label="pion two-point correlator",
            summary="A simpler pion two-point workflow is another plausible interpretation if the spectroscopy wording was informal.",
            confidence="low",
            status="candidate",
            task_type_hint="pion_2pt",
        )
        proposals, citations = _meson_spec_formula_proposals()
        physics.status = "needs_confirmation"
        physics.candidate_targets = [candidate, pion_candidate]
        physics.inferred_interpretation = candidate
        physics.task_type_hint = "meson_spec"
        physics.formula_proposals = proposals
        physics.local_references = list(MESON_SPEC_LOCAL_REFERENCE_SUFFIXES)
        physics.external_citations = citations
        physics.inferred_fields["target_id"] = MESON_SPEC_TARGET_ID
        return physics

    if _meson_correlator_like_request(lowered):
        proposals, citations, local_references = _ambiguous_meson_formula_proposals(lowered)
        physics.status = "needs_confirmation"
        physics.candidate_targets = _ambiguous_meson_candidates(lowered)
        inferred = next(
            (
                item
                for item in physics.candidate_targets
                if item.get("status") == "candidate" and item.get("confidence") in {"medium", "high"}
            ),
            physics.candidate_targets[0],
        )
        physics.inferred_interpretation = inferred
        physics.formula_proposals = proposals
        physics.local_references = local_references
        physics.external_citations = citations
        target_id = inferred.get("target_id")
        if isinstance(target_id, str):
            physics.inferred_fields["target_id"] = target_id
        return physics

    physics.status = "needs_confirmation"
    physics.candidate_targets = [
        _make_target(
            target_id=HADRON_UNSPECIFIED_TARGET_ID,
            label="hadron correlator target is underspecified",
            summary="The request does not yet identify a runnable hadron two-point target.",
            confidence="low",
            status="needs_confirmation",
            task_type_hint=None,
        )
    ]
    physics.inferred_interpretation = physics.candidate_targets[0]
    physics.formula_proposals, physics.external_citations, physics.local_references = _ambiguous_hadron_formula_proposals(lowered)
    return physics
