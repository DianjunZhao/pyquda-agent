"""Task schemas for the MVP."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field


@dataclass
class Pion2ptTaskDraft:
    user_request: str | None = None
    task_type: str | None = None
    workflow_id: str | None = None
    start_from: str | None = None
    has_existing_propagators: bool | None = None
    gauge_format: str | None = None
    gauge_path: str | None = None
    propagator_format: str | None = None
    propagator_paths: list[str] = field(default_factory=list)
    lattice_size: list[int] = field(default_factory=list)
    grid_size: list[int] = field(default_factory=list)
    fermion_action: str | None = None
    mass: float | None = None
    xi_0: float | None = None
    nu: float | None = None
    coeff_t: float | None = None
    coeff_r: float | None = None
    solver_tol: float | None = None
    solver_maxiter: int | None = None
    multigrid_blocks: list[list[int]] = field(default_factory=list)
    stout_smear_steps: int | None = None
    stout_smear_rho: float | None = None
    stout_smear_ndim: int | None = None
    source_smearing_kind: str | None = None
    source_smearing_rho: float | None = None
    source_smearing_steps: int | None = None
    flow_steps: int | None = None
    flow_epsilon: float | None = None
    source_type: str | None = None
    sink_type: str | None = None
    gamma_insertions: list[str] = field(default_factory=list)
    momentum_projection: str | None = None
    momenta: list[list[int]] = field(default_factory=list)
    source_timeslices: list[int] = field(default_factory=list)
    gauge_fixed: bool | None = None
    correlator_output_format: str | None = None
    correlator_output_path: str | None = None
    resource_path: str | None = None
    cluster_launch: str | None = None
    script_output_path: str | None = None
    script_style: str | None = None
    notes: str | None = None
    missing_fields: list[str] = field(default_factory=list)
    unsupported_reasons: list[str] = field(default_factory=list)
    field_sources: dict[str, str] = field(default_factory=dict)
    inherited_fields: dict[str, object] = field(default_factory=dict)
    user_confirmed_fields: dict[str, object] = field(default_factory=dict)
    inferred_fields: dict[str, object] = field(default_factory=dict)
    clarified_fields: dict[str, object] = field(default_factory=dict)
    parser_guesses: dict[str, object] = field(default_factory=dict)
    fixed_fields: dict[str, object] = field(default_factory=dict)
    unsupported_fields: dict[str, str] = field(default_factory=dict)
    chosen_workflow_target: str | None = None
    pyquda_references: list[str] = field(default_factory=list)
    external_citations: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Pion2ptTaskDraft":
        return cls(**data)


@dataclass
class Pion2ptTask:
    task_type: str
    workflow_id: str
    start_from: str
    has_existing_propagators: bool
    gauge_format: str
    gauge_path: str
    propagator_format: str | None
    propagator_paths: list[str]
    lattice_size: list[int]
    grid_size: list[int]
    fermion_action: str
    mass: float
    xi_0: float
    nu: float
    coeff_t: float
    coeff_r: float
    solver_tol: float
    solver_maxiter: int
    multigrid_blocks: list[list[int]]
    stout_smear_steps: int | None
    stout_smear_rho: float | None
    stout_smear_ndim: int | None
    source_type: str
    sink_type: str
    gamma_insertions: list[str]
    momentum_projection: str
    momenta: list[list[int]]
    source_timeslices: list[int]
    gauge_fixed: bool
    correlator_output_format: str
    correlator_output_path: str
    resource_path: str
    cluster_launch: str | None
    script_output_path: str
    script_style: str
    field_sources: dict[str, str]
    flow_steps: int | None = None
    flow_epsilon: float | None = None
    notes: str | None = None
    source_smearing_kind: str | None = None
    source_smearing_rho: float | None = None
    source_smearing_steps: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)
