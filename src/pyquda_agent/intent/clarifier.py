"""Clarification logic for physics-target interpretation."""

from __future__ import annotations

from .interpreter import APE_SMEAR_TARGET_ID
from .interpreter import BARYON_UNSPECIFIED_TARGET_ID
from .interpreter import HADRON_UNSPECIFIED_TARGET_ID
from .interpreter import HYP_SMEAR_TARGET_ID
from .interpreter import MESON_SPEC_TARGET_ID
from .interpreter import MESON_UNSPECIFIED_TARGET_ID
from .interpreter import NEUTRON_TARGET_ID
from .interpreter import PION_PCAC_TARGET_ID
from .interpreter import PION_DISPERSION_TARGET_ID
from .interpreter import PION_TARGET_ID
from .interpreter import PROTON_TARGET_ID
from .interpreter import QUARK_PROPAGATOR_TARGET_ID
from .interpreter import RHO_TARGET_ID
from .interpreter import STOUT_SMEAR_TARGET_ID
from .interpreter import WILSON_FLOW_TARGET_ID
from .interpreter import interpret_request
from .schema import ClarifyingQuestion
from .schema import PhysicsTargetArtifact


_HADRON_WORKFLOW_ASSUMPTION_SUMMARY = (
    "pion -> wall/local/zero momentum（或 existing propagator entry）；"
    "pion pcac -> wall/local/zero momentum ratio；"
    "pion dispersion -> point/local/fixed momentum list；"
    "meson spectrum -> wall source + gamma5/gamma4gamma5 + |p|^2<=9；"
    "rho/vector -> wall/local/spatial gamma_i/zero momentum（或 existing propagator entry）；"
    "proton -> wall/local/zero momentum（或 existing propagator entry）。"
)

_UTILITY_WORKFLOW_ASSUMPTION_SUMMARY = (
    "quark propagator -> gauge entry + one stout-smear step + Clover point source + HDF5 propagator；"
    "gaussian-shell quark propagator -> gauge entry + point-source seed + gaussianSmear(2.0, 5) + Clover invertPropagator + HDF5 propagator；"
    "Wilson flow -> gauge entry + wilsonFlowChroma(flow_steps, flow_epsilon) + npy energy history；"
    "stout smear -> gauge entry + stoutSmear(1, 0.241, 3) + npy gauge output；"
    "APE smear -> gauge entry + apeSmearChroma(1, 2.5, 4) + npy gauge output；"
    "HYP smear -> gauge entry + hypSmear(1, 0.75, 0.6, 0.3, 4) + npy gauge output。"
)

_MESON_SIDE_TARGET_IDS = {
    MESON_UNSPECIFIED_TARGET_ID,
    MESON_SPEC_TARGET_ID,
    PION_TARGET_ID,
    PION_PCAC_TARGET_ID,
    PION_DISPERSION_TARGET_ID,
    RHO_TARGET_ID,
}

_BARYON_SIDE_TARGET_IDS = {
    BARYON_UNSPECIFIED_TARGET_ID,
    PROTON_TARGET_ID,
    NEUTRON_TARGET_ID,
}

_UNSPECIFIED_HADRON_TARGET_IDS = {
    HADRON_UNSPECIFIED_TARGET_ID,
    MESON_UNSPECIFIED_TARGET_ID,
    BARYON_UNSPECIFIED_TARGET_ID,
}


def _candidate_answer_alias(target_id: str) -> str:
    if target_id == PION_TARGET_ID:
        return "pion"
    if target_id == PION_PCAC_TARGET_ID:
        return "pion pcac"
    if target_id == PION_DISPERSION_TARGET_ID:
        return "pion dispersion"
    if target_id == MESON_SPEC_TARGET_ID:
        return "meson spectrum"
    if target_id == RHO_TARGET_ID:
        return "rho"
    if target_id == PROTON_TARGET_ID:
        return "proton"
    if target_id == NEUTRON_TARGET_ID:
        return "neutron"
    if target_id == QUARK_PROPAGATOR_TARGET_ID:
        return "quark propagator"
    if target_id == WILSON_FLOW_TARGET_ID:
        return "wilson flow"
    if target_id == STOUT_SMEAR_TARGET_ID:
        return "stout smear"
    if target_id == APE_SMEAR_TARGET_ID:
        return "ape smear"
    if target_id == HYP_SMEAR_TARGET_ID:
        return "hyp smear"
    if target_id == HADRON_UNSPECIFIED_TARGET_ID:
        return "hadron"
    if target_id == BARYON_UNSPECIFIED_TARGET_ID:
        return "baryon"
    return "meson"


def _candidate_prompt_summary(physics: PhysicsTargetArtifact, *, max_items: int = 3) -> str:
    lines: list[str] = []
    for candidate in physics.candidate_targets[:max_items]:
        target_id = candidate.get("target_id")
        label = candidate.get("label")
        summary = candidate.get("summary")
        if not isinstance(target_id, str) or not isinstance(label, str):
            continue
        alias = _candidate_answer_alias(target_id)
        if isinstance(summary, str) and summary:
            lines.append(f"{alias}: {label}; {summary}")
        else:
            lines.append(f"{alias}: {label}")
    return "；".join(lines)


def _compact_prompt_text(value: object, *, limit: int = 96) -> str | None:
    if not isinstance(value, str):
        return None
    compact = " ".join(value.split())
    if not compact:
        return None
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _formula_prompt_summary(
    physics: PhysicsTargetArtifact,
    *,
    max_items: int = 2,
    include_convention: bool = False,
) -> str:
    lines: list[str] = []
    for proposal in physics.formula_proposals[:max_items]:
        if not isinstance(proposal, dict):
            continue
        target_id = proposal.get("target_id")
        label = _compact_prompt_text(proposal.get("label"), limit=72)
        operator = _compact_prompt_text(proposal.get("operator"), limit=84)
        convention = _compact_prompt_text(proposal.get("convention"), limit=96)
        if not isinstance(target_id, str) or not label:
            continue
        alias = _candidate_answer_alias(target_id)
        parts = [f"{alias}: {label}"]
        if operator:
            parts.append(f"operator={operator}")
        if include_convention and convention:
            parts.append(f"assumption={convention}")
        lines.append("; ".join(parts))
    return "；".join(lines)


def _request_is_hadron_like(user_request: str) -> bool:
    lowered = user_request.lower()
    return any(
        token in lowered
        for token in (
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
        )
    )


def _specific_hadron_choice_aliases(physics: PhysicsTargetArtifact, *, max_items: int = 2) -> list[str]:
    tail_targets = [item.get("target_id") for item in physics.candidate_targets[1:] if isinstance(item, dict)]
    if any(target_id in {MESON_UNSPECIFIED_TARGET_ID, BARYON_UNSPECIFIED_TARGET_ID} for target_id in tail_targets):
        return []
    aliases: list[str] = []
    for target_id in tail_targets:
        if not isinstance(target_id, str) or target_id in _UNSPECIFIED_HADRON_TARGET_IDS:
            continue
        alias = _candidate_answer_alias(target_id)
        if alias and alias not in aliases:
            aliases.append(alias)
        if len(aliases) >= max_items:
            break
    return aliases


def _promote_existing_or_refined_branch(
    physics: PhysicsTargetArtifact,
    *,
    target_ids: set[str],
    fallback_request: str,
) -> None:
    candidate = next((item for item in physics.candidate_targets if item.get("target_id") in target_ids), None)
    if candidate is None or candidate.get("target_id") in {MESON_UNSPECIFIED_TARGET_ID, BARYON_UNSPECIFIED_TARGET_ID}:
        refined = interpret_request(fallback_request)
        physics.status = refined.status
        physics.candidate_targets = refined.candidate_targets
        physics.inferred_interpretation = refined.inferred_interpretation
        physics.confirmed_interpretation = refined.confirmed_interpretation
        physics.formula_proposals = refined.formula_proposals
        physics.task_type_hint = refined.task_type_hint
        physics.local_references = refined.local_references
        physics.external_citations = refined.external_citations
        return
    physics.status = "needs_confirmation"
    physics.inferred_interpretation = candidate
    physics.task_type_hint = candidate.get("task_type_hint")


def _generic_capability_prompt(
    physics: PhysicsTargetArtifact,
    *,
    include_formula_summary: bool,
) -> str:
    candidate_summary = _candidate_prompt_summary(physics)
    candidate_suffix = f" 当前候选包括：{candidate_summary}。" if candidate_summary else ""
    formula_summary = (
        _formula_prompt_summary(physics, max_items=3, include_convention=False) if include_formula_summary else ""
    )
    formula_suffix = f" 候选公式/operator/假设包括：{formula_summary}。" if formula_summary else ""
    return (
        "请先明确你要的物理/实现目标。当前系统支持的 grounded workflow family 分为两类："
        f" Hadron correlators: {_HADRON_WORKFLOW_ASSUMPTION_SUMMARY}"
        f" Gauge/solver utilities: {_UTILITY_WORKFLOW_ASSUMPTION_SUMMARY}"
        f"{candidate_suffix}"
        f"{formula_suffix}"
        "如果你要零动量 pion 2pt，请回答 pion；如果你要 PCAC ratio，请回答 pion pcac；"
        "如果你要动量投影 pion correlator，请回答 pion dispersion；"
        "如果你要 meson spectroscopy 路径，请回答 meson spectrum；"
        "如果你要 rho/vector meson，请回答 rho；如果你要 proton 2pt，请回答 proton；"
        "如果你要 quark propagator，请回答 quark propagator；"
        "如果你要 Wilson flow，请回答 wilson flow；"
        "如果你要 gauge smearing，请明确回答 stout smear、ape smear 或 hyp smear。"
        "如果这些都不是你的目标，请直接给出明确 hadron/channel 或 gauge utility 目标，"
        "系统会如实报告当前是否支持。完整公式和来源见 physics_formula_preview 与 .physics.json。"
    )


def build_physics_questions(physics: PhysicsTargetArtifact, max_questions: int) -> list[ClarifyingQuestion]:
    if physics.confirmed_interpretation is not None:
        return []

    inferred = physics.inferred_interpretation or {}
    target_id = inferred.get("target_id")
    questions: list[ClarifyingQuestion] = []
    if target_id == PION_TARGET_ID:
        questions.append(
            ClarifyingQuestion(
                field_name="confirmed_target_id",
                prompt=(
                    "当前推断目标是 pion two-point correlator，采用规范的 pseudoscalar pion operator。"
                    "请确认目标；可回答 pion、yes，或明确说明其他 hadron/channel。"
                ),
                category="physics",
                scope="physics",
            )
        )
    elif target_id == PION_DISPERSION_TARGET_ID:
        questions.append(
            ClarifyingQuestion(
                field_name="confirmed_target_id",
                prompt=(
                    "当前推断目标是 pion dispersion correlator：使用 pseudoscalar pion operator，"
                    "并对一组固定动量做 momentum projection。请确认；可回答 pion dispersion、dispersion、yes，"
                    "或明确改成 pion two-point / 其他 hadron/channel。"
                ),
                category="physics",
                scope="physics",
            )
        )
    elif target_id == PION_PCAC_TARGET_ID:
        questions.append(
            ClarifyingQuestion(
                field_name="confirmed_target_id",
                prompt=(
                    "当前推断目标是 pion pcac ratio correlator：使用本地 `4_Pion_PCAC.py` 路径里的 wall source、"
                    "pion / pionA4 两条零动量收缩，并形成 C_A4P / C_PP 比值。请确认；可回答 pion pcac、pcac、yes，"
                    "或明确改成 pion / pion dispersion / proton。"
                ),
                category="physics",
                scope="physics",
            )
        )
    elif target_id == MESON_SPEC_TARGET_ID:
        questions.append(
            ClarifyingQuestion(
                field_name="confirmed_target_id",
                prompt=(
                    "当前推断目标是 meson spectrum correlator：使用本地 mesonspec 路径里的固定 wall-source、"
                    "gamma5 / gamma4gamma5 插入族和 |p|^2<=9 动量族。请确认；可回答 meson spectrum、mesonspec、yes，"
                    "或明确改成 pion / pion dispersion / proton。"
                ),
                category="physics",
                scope="physics",
            )
        )
    elif target_id == RHO_TARGET_ID:
        questions.append(
            ClarifyingQuestion(
                field_name="confirmed_target_id",
                prompt=(
                    "当前推断目标是 rho/vector meson correlator：按标准 vector-meson channel 可写成 "
                    "O_rho,i(x)=qbar(x) gamma_i q(x)。当前 grounded rho family 被锁定为："
                    "gauge entry 或 existing propagator entry、wall source、local sink、spatial gamma_i family、zero momentum、npy 输出。"
                    "如果你要这条当前 grounded rho/vector workflow，请回答 rho、vector meson 或 yes；"
                    "如果你实际想要更宽的 meson spectroscopy gamma5/gamma4gamma5 family，请回答 meson spectrum；"
                    "如果你实际想要 pion，请回答 pion 或 pion dispersion。"
                ),
                category="physics",
                scope="physics",
            )
        )
    elif target_id == HADRON_UNSPECIFIED_TARGET_ID:
        if not _request_is_hadron_like(physics.user_request):
            prompt = _generic_capability_prompt(physics, include_formula_summary=True)
        else:
            candidate_summary = _candidate_prompt_summary(physics, max_items=4)
            candidate_suffix = f" 当前候选包括：{candidate_summary}。" if candidate_summary else ""
            formula_summary = _formula_prompt_summary(physics, max_items=4, include_convention=False)
            formula_suffix = f" 候选公式/operator/假设包括：{formula_summary}。" if formula_summary else ""
            direct_aliases = _specific_hadron_choice_aliases(physics)
            if direct_aliases:
                if len(direct_aliases) == 1:
                    direct_summary = direct_aliases[0]
                else:
                    direct_summary = " / ".join(direct_aliases)
                prompt = (
                    "请先确认更具体的 hadron target。当前请求已经把候选收窄到 "
                    f"{direct_summary}。"
                    f"{candidate_suffix}"
                    f"{formula_suffix}"
                    f"当前 grounded hadron workflow 假设包括：{_HADRON_WORKFLOW_ASSUMPTION_SUMMARY}"
                    f"请直接回答 {direct_summary}；"
                    "如果你只想先确认大分支，也可以回答 meson 或 baryon。"
                    "其中 neutron 当前会保持 explicit unsupported，并给出最近 grounded proton alternative。"
                    "完整公式和来源见 physics_formula_preview 与 .physics.json。"
                )
            else:
                prompt = (
                    "请先明确 hadron channel。当前请求只说明了 hadron correlator，但还没有说明是 meson 还是 baryon。"
                    f"{candidate_suffix}"
                    f"{formula_suffix}"
                    f"当前 grounded hadron workflow 假设包括：{_HADRON_WORKFLOW_ASSUMPTION_SUMMARY}"
                    "如果你要先走 meson 侧澄清，请回答 meson；如果你要先走 baryon / nucleon 侧澄清，请回答 baryon；"
                    "如果你已经知道更具体目标，也可以直接回答 pion、pion pcac、pion dispersion、meson spectrum、rho、proton 或 neutron。"
                    "其中 neutron 当前会保持 explicit unsupported，并给出最近 grounded proton alternative。"
                    "完整公式和来源见 physics_formula_preview 与 .physics.json。"
                )
        questions.append(
            ClarifyingQuestion(
                field_name="confirmed_target_id",
                prompt=prompt,
                category="physics",
                scope="physics",
            )
        )
    elif target_id == MESON_UNSPECIFIED_TARGET_ID:
        if not _request_is_hadron_like(physics.user_request):
            prompt = _generic_capability_prompt(physics, include_formula_summary=True)
        else:
            candidate_summary = _candidate_prompt_summary(physics)
            candidate_suffix = f" 当前候选包括：{candidate_summary}。" if candidate_summary else ""
            formula_summary = _formula_prompt_summary(physics, max_items=3, include_convention=False)
            formula_suffix = f" 候选公式/operator/假设包括：{formula_summary}。" if formula_summary else ""
            prompt = (
                "请先明确物理目标。当前支持 pion two-point correlator、pion pcac ratio correlator、pion dispersion correlator、"
                "meson spectrum correlator、rho/vector meson correlator、proton two-point correlator。"
                f"{candidate_suffix}"
                f"{formula_suffix}"
                f"当前 grounded workflow 假设包括：{_HADRON_WORKFLOW_ASSUMPTION_SUMMARY}"
                "如果你要零动量 pion 2pt，请回答 pion；如果你要 PCAC ratio，请回答 pion pcac；如果你要动量投影/dispersion，请回答 pion dispersion；"
                "如果你要 meson spectroscopy 路径，请回答 meson spectrum；如果你要 rho/vector meson，请回答 rho；如果你要 proton 2pt，请回答 proton；"
                "如果你实际不是 hadron correlator，也可以直接回答 quark propagator、wilson flow、stout smear、ape smear 或 hyp smear。"
                "否则请给出明确 hadron/channel，系统会如实报告是否暂不支持。完整公式和来源见 physics_formula_preview 与 .physics.json。"
            )
        questions.append(
            ClarifyingQuestion(
                field_name="confirmed_target_id",
                prompt=prompt,
                category="physics",
                scope="physics",
            )
        )
    elif target_id == BARYON_UNSPECIFIED_TARGET_ID:
        candidate_summary = _candidate_prompt_summary(physics, max_items=3)
        candidate_suffix = f" 当前候选包括：{candidate_summary}。" if candidate_summary else ""
        formula_summary = _formula_prompt_summary(physics, max_items=3, include_convention=False)
        formula_suffix = f" 候选公式/operator/假设包括：{formula_summary}。" if formula_summary else ""
        questions.append(
            ClarifyingQuestion(
                field_name="confirmed_target_id",
                prompt=(
                    "请先明确 baryon/nucleon channel。当前本地可运行 baryon workflow 只有 proton two-point correlator。"
                    f"{candidate_suffix}"
                    f"{formula_suffix}"
                    "当前 grounded proton workflow 被锁定为：gauge entry 或 existing propagator entry、wall source、local sink、zero momentum、npy 输出。"
                    "如果你就是要 proton 2pt，请回答 proton；如果你指的是 neutron，请回答 neutron，系统会显式返回 unsupported 并给最近 grounded alternative；"
                    "如果你指的是其他 nucleon/baryon channel，请明确名字，"
                    "系统会如实报告当前是否暂不支持。完整公式和来源见 physics_formula_preview 与 .physics.json。"
                ),
                category="physics",
                scope="physics",
            )
        )
    elif target_id == PROTON_TARGET_ID:
        questions.append(
            ClarifyingQuestion(
                field_name="confirmed_target_id",
                prompt=(
                    "当前推断目标是 proton two-point correlator，采用本地 PyQUDA example 中的标准 proton operator 与零动量奇偶投影收缩。"
                    "请确认目标；可回答 proton、yes，或明确改成 pion / pion dispersion。"
                ),
                category="physics",
                scope="physics",
            )
        )
    elif target_id == QUARK_PROPAGATOR_TARGET_ID:
        point_branch = any(
            item.get("proposal_id") == "quark_propagator_point_source_clover" for item in physics.formula_proposals
        )
        gaussian_branch = any(
            item.get("proposal_id") == "quark_propagator_gaussian_shell_source_clover" for item in physics.formula_proposals
        )
        questions.append(
            ClarifyingQuestion(
                field_name="confirmed_target_id",
                prompt=(
                    "当前推断目标是 quark propagator，但当前 grounded local implementation branch 还需要确认。"
                    "当前本地有两条可运行分支："
                    "point-source branch 使用 `2_Quark_Propagator.py` / `test_io.py` 路径里的 "
                    "Chroma/QIO gauge -> one stout-smear step -> Clover solve -> point source at [0,0,0,t_src] -> HDF5 propagator；"
                    "gaussian-shell branch 使用 `test_gaussian.py` / `test_io.py` 路径里的 "
                    "Chroma/QIO gauge -> point-source seed propagator -> gaussianSmear(rho=2.0, n_steps=5) -> "
                    "getClover/invertPropagator -> HDF5 propagator。"
                    "如果你要默认 point-source quark propagator，请回答 quark propagator、point propagator、propagator 或 yes；"
                    "如果你要 gaussian-shell branch，请回答 gaussian shell propagator；"
                    "如果你实际想要从 existing propagators 构造 hadron correlator，请明确回答 pion、proton、meson spectrum 或 rho。"
                )
                if point_branch and gaussian_branch
                else (
                    "当前推断目标是 quark propagator：使用本地 `test_gaussian.py` / `test_io.py` 路径里的 "
                    "Chroma/QIO gauge -> point-source propagator at [0,0,0,t_src] -> gaussianSmear(rho=2.0, n_steps=5) "
                    "-> Clover solve via getClover/invertPropagator -> HDF5 propagator 保存。"
                    "当前 grounded gaussian-shell quark-propagator family 被锁定为 gauge entry、固定 gaussian shell 参数、单一 propagator 输出，不是 hadron correlator workflow。"
                    "请确认目标；可回答 quark propagator、gaussian shell propagator、propagator、yes，或明确改成 hadron correlator workflow。"
                )
                if gaussian_branch
                else (
                    "当前推断目标是 quark propagator：使用本地 `2_Quark_Propagator.py` / `test_io.py` 路径里的 "
                    "Chroma/QIO gauge -> one stout-smear step -> Clover solve -> point source at [0,0,0,t_src] -> HDF5 propagator 保存。"
                    "当前 grounded quark-propagator family 被锁定为 gauge entry、单一 point source、单一 propagator 输出，不是 hadron correlator workflow。"
                    "请确认目标；可回答 quark propagator、propagator、yes，或明确改成 hadron correlator workflow。"
                ),
                category="physics",
                scope="physics",
            )
        )
    elif target_id == WILSON_FLOW_TARGET_ID:
        questions.append(
            ClarifyingQuestion(
                field_name="confirmed_target_id",
                prompt=(
                    "当前推断目标是 Wilson flow / gradient flow：使用本地 `test_wflow.py` 路径里的 "
                    "QIO gauge -> gauge.copy() -> wilsonFlowChroma(flow_steps, flow_epsilon) -> npy energy history。"
                    "当前 grounded Wilson-flow family 被锁定为 gauge entry + energy-history 输出，不进入 propagator / hadron contraction 分支。"
                    "请确认目标；可回答 wilson flow、gradient flow、yes，或明确改成 hadron correlator / propagator workflow。"
                ),
                category="physics",
                scope="physics",
            )
        )
    elif target_id == STOUT_SMEAR_TARGET_ID:
        candidate_summary = _candidate_prompt_summary(physics)
        candidate_suffix = f" 当前候选包括：{candidate_summary}。" if candidate_summary else ""
        formula_summary = _formula_prompt_summary(physics, max_items=3, include_convention=False)
        formula_suffix = f" 候选公式/operator/假设包括：{formula_summary}。" if formula_summary else ""
        questions.append(
            ClarifyingQuestion(
                field_name="confirmed_target_id",
                prompt=(
                    "当前推断目标是 stout-smeared gauge configuration：使用本地 `test_smear.py` / `test_io.py` 路径里的 "
                    "QIO gauge -> gauge.copy() -> stoutSmear(1, 0.241, 3) -> npy smeared gauge 保存。"
                    "当前 grounded stout-smear family 被锁定为 gauge entry、单步固定参数 smearing、单一 npy 输出。"
                    f"{candidate_suffix}"
                    f"{formula_suffix}"
                    "如果你要当前 grounded stout-smear family，请回答 stout smear 或 yes；"
                    "如果你实际想要 APE smear，请明确回答 ape smear，系统会切到对应的 runnable APE workflow；"
                    "如果你实际想要 HYP smear，请明确回答 hyp smear，系统会切到对应的 runnable HYP workflow；"
                    "否则也可以明确改成 Wilson flow / hadron correlator / propagator workflow。完整公式和来源见 physics_formula_preview 与 .physics.json。"
                ),
                category="physics",
                scope="physics",
            )
        )
    elif target_id == APE_SMEAR_TARGET_ID:
        candidate_summary = _candidate_prompt_summary(physics)
        candidate_suffix = f" 当前候选包括：{candidate_summary}。" if candidate_summary else ""
        formula_summary = _formula_prompt_summary(physics, max_items=3, include_convention=False)
        formula_suffix = f" 候选公式/operator/假设包括：{formula_summary}。" if formula_summary else ""
        questions.append(
            ClarifyingQuestion(
                field_name="confirmed_target_id",
                prompt=(
                    "当前推断目标是 APE-smeared gauge configuration：使用本地 `test_smear.py` / `test_io.py` 路径里的 "
                    "QIO gauge -> gauge.copy() -> apeSmearChroma(1, 2.5, 4) -> npy smeared gauge 保存。"
                    "当前 grounded APE-smear family 被锁定为 gauge entry、单步固定参数 smearing、单一 npy 输出。"
                    f"{candidate_suffix}"
                    f"{formula_suffix}"
                    "如果你要当前 grounded APE-smear family，请回答 ape smear 或 yes；"
                    "如果你实际想要 stout smear，请明确回答 stout smear，系统会切到对应的 runnable stout workflow；"
                    "如果你实际想要 HYP smear，请明确回答 hyp smear，系统会切到对应的 runnable HYP workflow；"
                    "否则也可以明确改成 Wilson flow / hadron correlator / propagator workflow。完整公式和来源见 physics_formula_preview 与 .physics.json。"
                ),
                category="physics",
                scope="physics",
            )
        )
    elif target_id == HYP_SMEAR_TARGET_ID:
        candidate_summary = _candidate_prompt_summary(physics)
        candidate_suffix = f" 当前候选包括：{candidate_summary}。" if candidate_summary else ""
        formula_summary = _formula_prompt_summary(physics, max_items=3, include_convention=False)
        formula_suffix = f" 候选公式/operator/假设包括：{formula_summary}。" if formula_summary else ""
        questions.append(
            ClarifyingQuestion(
                field_name="confirmed_target_id",
                prompt=(
                    "当前推断目标是 HYP-smeared gauge configuration：使用本地 `test_smear.py` / `test_io.py` 路径里的 "
                    "QIO gauge -> gauge.copy() -> hypSmear(1, 0.75, 0.6, 0.3, 4) -> npy smeared gauge 保存。"
                    "当前 grounded HYP-smear family 被锁定为 gauge entry、单步固定参数 smearing、单一 npy 输出。"
                    f"{candidate_suffix}"
                    f"{formula_suffix}"
                    "如果你要当前 grounded HYP-smear family，请回答 hyp smear 或 yes；"
                    "如果你实际想要 APE smear，请明确回答 ape smear，系统会切到对应的 runnable APE workflow；"
                    "如果你实际想要 stout smear，请明确回答 stout smear，系统会切到对应的 runnable stout workflow；"
                    "否则也可以明确改成 Wilson flow / hadron correlator / propagator workflow。完整公式和来源见 physics_formula_preview 与 .physics.json。"
                ),
                category="physics",
                scope="physics",
            )
        )
    else:
        questions.append(
            ClarifyingQuestion(
                field_name="confirmed_target_id",
                prompt=_generic_capability_prompt(physics, include_formula_summary=True),
                category="physics",
                scope="physics",
            )
        )
    return questions[:max_questions]


def _set_confirmed_target(physics: PhysicsTargetArtifact, target_id: str, source: str) -> None:
    candidate = next((item for item in physics.candidate_targets if item.get("target_id") == target_id), None)
    if candidate is None:
        candidate = interpret_request(target_id.replace("_", " ")).inferred_interpretation
    physics.confirmed_interpretation = candidate
    physics.status = "confirmed"
    physics.clarified_fields["target_id"] = target_id
    physics.clarification_trace.append(
        {
            "field_name": "confirmed_target_id",
            "answer": source,
            "resolution": target_id,
            "category": "physics",
            "scope": "physics",
        }
    )
    if target_id == PION_TARGET_ID:
        physics.task_type_hint = "pion_2pt"
        physics.unsupported_fields.pop("target_id", None)
        physics.unsupported_reasons = [
            reason for reason in physics.unsupported_reasons if "Only pion two-point correlators" not in reason
        ]
    elif target_id == PION_DISPERSION_TARGET_ID:
        physics.task_type_hint = "pion_dispersion"
        physics.unsupported_fields.pop("target_id", None)
        physics.unsupported_reasons = [
            reason for reason in physics.unsupported_reasons if "Only pion" not in reason
        ]
    elif target_id == PION_PCAC_TARGET_ID:
        physics.task_type_hint = "pion_pcac"
        physics.unsupported_fields.pop("target_id", None)
        physics.unsupported_reasons = [
            reason for reason in physics.unsupported_reasons if "Only pion" not in reason
        ]
    elif target_id == MESON_SPEC_TARGET_ID:
        physics.task_type_hint = "meson_spec"
        physics.unsupported_fields.pop("target_id", None)
        physics.unsupported_reasons = [
            reason for reason in physics.unsupported_reasons if "Only pion" not in reason
        ]
    elif target_id == RHO_TARGET_ID:
        physics.task_type_hint = "rho_vector"
        physics.unsupported_fields.pop("target_id", None)
        physics.unsupported_reasons = []
    elif target_id == PROTON_TARGET_ID:
        physics.task_type_hint = "proton_2pt"
        physics.unsupported_fields.pop("target_id", None)
        physics.unsupported_reasons = []
    elif target_id == NEUTRON_TARGET_ID:
        physics.task_type_hint = None
        physics.unsupported_fields["target_id"] = (
            "Neutron two-point correlators are not implemented in the current grounded local workflow catalog."
        )
        physics.unsupported_reasons = [
            "Neutron two-point correlators are not implemented in the current grounded local workflow catalog."
        ]
    elif target_id == QUARK_PROPAGATOR_TARGET_ID:
        physics.task_type_hint = "quark_propagator"
        physics.unsupported_fields.pop("target_id", None)
        physics.unsupported_reasons = []
    elif target_id == WILSON_FLOW_TARGET_ID:
        physics.task_type_hint = "wilson_flow"
        physics.unsupported_fields.pop("target_id", None)
        physics.unsupported_reasons = []
    elif target_id == STOUT_SMEAR_TARGET_ID:
        physics.task_type_hint = "stout_smear"
        physics.unsupported_fields.pop("target_id", None)
        physics.unsupported_reasons = []
    elif target_id == APE_SMEAR_TARGET_ID:
        physics.task_type_hint = "ape_smear"
        physics.unsupported_fields.pop("target_id", None)
        physics.unsupported_reasons = []
    elif target_id == HYP_SMEAR_TARGET_ID:
        physics.task_type_hint = "hyp_smear"
        physics.unsupported_fields.pop("target_id", None)
        physics.unsupported_reasons = []


def _set_quark_propagator_branch(physics: PhysicsTargetArtifact, branch: str | None) -> None:
    if branch == "gaussian_shell":
        physics.inferred_fields["source_smearing_kind"] = "gaussian_shell"
        physics.clarified_fields["source_smearing_kind"] = "gaussian_shell"
        return
    physics.inferred_fields.pop("source_smearing_kind", None)
    physics.clarified_fields.pop("source_smearing_kind", None)


def apply_physics_answer(physics: PhysicsTargetArtifact, field_name: str, answer: str) -> None:
    if field_name != "confirmed_target_id":
        return

    lowered = answer.strip().lower()
    inferred_target_id = (physics.inferred_interpretation or {}).get("target_id")
    if lowered in {"yes", "y"}:
        if inferred_target_id == PION_DISPERSION_TARGET_ID:
            _set_confirmed_target(physics, PION_DISPERSION_TARGET_ID, answer)
        elif inferred_target_id == PION_PCAC_TARGET_ID:
            _set_confirmed_target(physics, PION_PCAC_TARGET_ID, answer)
        elif inferred_target_id == MESON_SPEC_TARGET_ID:
            _set_confirmed_target(physics, MESON_SPEC_TARGET_ID, answer)
        elif inferred_target_id == RHO_TARGET_ID:
            _set_confirmed_target(physics, RHO_TARGET_ID, answer)
        elif inferred_target_id == PROTON_TARGET_ID:
            _set_confirmed_target(physics, PROTON_TARGET_ID, answer)
        elif inferred_target_id == NEUTRON_TARGET_ID:
            _set_confirmed_target(physics, NEUTRON_TARGET_ID, answer)
        elif inferred_target_id == WILSON_FLOW_TARGET_ID:
            _set_confirmed_target(physics, WILSON_FLOW_TARGET_ID, answer)
        elif inferred_target_id == APE_SMEAR_TARGET_ID:
            _set_confirmed_target(physics, APE_SMEAR_TARGET_ID, answer)
        elif inferred_target_id == HYP_SMEAR_TARGET_ID:
            _set_confirmed_target(physics, HYP_SMEAR_TARGET_ID, answer)
        elif inferred_target_id == STOUT_SMEAR_TARGET_ID:
            _set_confirmed_target(physics, STOUT_SMEAR_TARGET_ID, answer)
        elif inferred_target_id == HADRON_UNSPECIFIED_TARGET_ID:
            candidate = next((item for item in physics.candidate_targets if item.get("target_id") == HADRON_UNSPECIFIED_TARGET_ID), None)
            if candidate is not None:
                physics.inferred_interpretation = candidate
            physics.status = "needs_confirmation"
            physics.task_type_hint = None
            physics.clarified_fields["target_id"] = HADRON_UNSPECIFIED_TARGET_ID
            physics.clarification_trace.append(
                {
                    "field_name": "confirmed_target_id",
                    "answer": answer,
                    "resolution": HADRON_UNSPECIFIED_TARGET_ID,
                    "category": "physics",
                    "scope": "physics",
                }
            )
        else:
            _set_confirmed_target(physics, PION_TARGET_ID, answer)
        return
    if lowered in {
        "pion pcac",
        "pcac",
        "pion_pcac",
        "pcac ratio",
        "pion pcac ratio",
    }:
        _set_confirmed_target(physics, PION_PCAC_TARGET_ID, answer)
        return
    if lowered in {
        "pion dispersion",
        "dispersion",
        "pion_dispersion",
        "pion momentum",
        "momentum projected pion",
    }:
        _set_confirmed_target(physics, PION_DISPERSION_TARGET_ID, answer)
        return
    if lowered in {"pion", "pion_2pt", "pion two-point", "pion two point"}:
        _set_confirmed_target(physics, PION_TARGET_ID, answer)
        return
    if lowered in {
        "meson spectrum",
        "meson spectroscopy",
        "meson_spec",
        "mesonspec",
        "meson spectrum correlator",
    }:
        _set_confirmed_target(physics, MESON_SPEC_TARGET_ID, answer)
        return
    if lowered in {
        "rho",
        "rho meson",
        "vector meson",
        "rho/vector meson",
        "vector meson correlator",
        "rho correlator",
    }:
        _set_confirmed_target(physics, RHO_TARGET_ID, answer)
        return
    if lowered in {"proton", "proton 2pt", "proton two-point"} or "proton" in lowered:
        _set_confirmed_target(physics, PROTON_TARGET_ID, answer)
        return
    if lowered in {"neutron", "neutron 2pt", "neutron two-point"} or "neutron" in lowered:
        _set_confirmed_target(physics, NEUTRON_TARGET_ID, answer)
        return
    if lowered in {
        "quark propagator",
        "point propagator",
        "point-source propagator",
        "point source propagator",
        "propagator",
    }:
        _set_quark_propagator_branch(physics, None)
        _set_confirmed_target(physics, QUARK_PROPAGATOR_TARGET_ID, answer)
        return
    if lowered in {
        "gaussian shell propagator",
        "gaussian-shell propagator",
        "gaussian shell quark propagator",
        "gaussian-shell quark propagator",
        "shell propagator",
        "shell-source propagator",
        "shell source propagator",
    }:
        _set_quark_propagator_branch(physics, "gaussian_shell")
        _set_confirmed_target(physics, QUARK_PROPAGATOR_TARGET_ID, answer)
        return
    if lowered in {"wilson flow", "gradient flow", "gauge flow", "wilson-flow", "gradient-flow"}:
        _set_confirmed_target(physics, WILSON_FLOW_TARGET_ID, answer)
        return
    if lowered in {"ape smear", "ape-smear", "ape smeared gauge", "ape-smeared gauge"}:
        _set_confirmed_target(physics, APE_SMEAR_TARGET_ID, answer)
        return
    if lowered in {"hyp smear", "hyp-smear", "hyp smeared gauge", "hyp-smeared gauge"}:
        _set_confirmed_target(physics, HYP_SMEAR_TARGET_ID, answer)
        return
    if lowered in {"stout smear", "stout-smear", "stout smeared gauge", "stout-smeared gauge", "gauge smearing"}:
        _set_confirmed_target(physics, STOUT_SMEAR_TARGET_ID, answer)
        return
    if lowered in {"meson", "meson correlator", "meson two-point", "meson two point", "meson 2pt"}:
        _promote_existing_or_refined_branch(
            physics,
            target_ids=_MESON_SIDE_TARGET_IDS,
            fallback_request="meson correlator",
        )
        physics.clarified_fields["target_id"] = MESON_UNSPECIFIED_TARGET_ID
        physics.clarification_trace.append(
            {
                "field_name": "confirmed_target_id",
                "answer": answer,
                "resolution": MESON_UNSPECIFIED_TARGET_ID,
                "category": "physics",
                "scope": "physics",
            }
        )
        return
    if lowered in {
        "hadron",
        "hadron correlator",
        "hadron two-point",
        "hadron two point",
        "hadron 2pt",
    }:
        candidate = next((item for item in physics.candidate_targets if item.get("target_id") == HADRON_UNSPECIFIED_TARGET_ID), None)
        if candidate is not None:
            physics.inferred_interpretation = candidate
        physics.status = "needs_confirmation"
        physics.task_type_hint = None
        physics.clarified_fields["target_id"] = HADRON_UNSPECIFIED_TARGET_ID
        physics.clarification_trace.append(
            {
                "field_name": "confirmed_target_id",
                "answer": answer,
                "resolution": HADRON_UNSPECIFIED_TARGET_ID,
                "category": "physics",
                "scope": "physics",
            }
        )
        return
    if lowered in {
        "baryon",
        "baryon 2pt",
        "baryon two-point",
        "nucleon correlator",
        "nucleon two-point",
        "nucleon two point",
    }:
        _promote_existing_or_refined_branch(
            physics,
            target_ids=_BARYON_SIDE_TARGET_IDS,
            fallback_request="baryon correlator",
        )
        physics.clarified_fields["target_id"] = BARYON_UNSPECIFIED_TARGET_ID
        physics.clarification_trace.append(
            {
                "field_name": "confirmed_target_id",
                "answer": answer,
                "resolution": BARYON_UNSPECIFIED_TARGET_ID,
                "category": "physics",
                "scope": "physics",
            }
        )
        return
    physics.status = "needs_confirmation"
