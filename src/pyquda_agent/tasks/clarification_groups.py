"""Grouped clarification helpers for stable task-field clusters."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable


CLOVER_SOLVER_PARAMETER_FIELDS = [
    "mass",
    "xi_0",
    "nu",
    "coeff_t",
    "coeff_r",
    "solver_tol",
    "solver_maxiter",
]

LATTICE_GEOMETRY_FIELDS = [
    "lattice_size",
    "grid_size",
]


@dataclass(frozen=True)
class ClarificationGroupDefinition:
    group_id: str
    label: str
    fields: list[str]
    parse_assignment: Callable[[str], list[tuple[str, str]]]
    build_value_example: Callable[[Callable[[str], str]], str]
    supported_input_modes: tuple[str, ...] = ("set",)
    recommended_input_mode: str = "set"


def _parse_clover_solver_parameters(raw_value: str) -> list[tuple[str, str]]:
    parts = [item for item in re.split(r"[\s,]+", raw_value.strip()) if item]
    if len(parts) != len(CLOVER_SOLVER_PARAMETER_FIELDS):
        raise ValueError(
            "--set clover_solver_parameters expects 7 comma- or space-separated values "
            "in the order mass, xi_0, nu, coeff_t, coeff_r, solver_tol, solver_maxiter."
        )
    return list(zip(CLOVER_SOLVER_PARAMETER_FIELDS, parts, strict=True))


def _parse_lattice_geometry(raw_value: str) -> list[tuple[str, str]]:
    if ";" not in raw_value:
        raise ValueError(
            "--set lattice_geometry expects two integer lists separated by ';' in the order "
            "lattice_size;grid_size, for example 24,24,24,72;1,1,1,2."
        )
    lattice_raw, grid_raw = raw_value.split(";", 1)
    lattice_values = re.findall(r"-?\d+", lattice_raw)
    grid_values = re.findall(r"-?\d+", grid_raw)
    if len(lattice_values) != 4 or len(grid_values) != 4:
        raise ValueError(
            "--set lattice_geometry expects exactly 4 lattice_size integers and 4 grid_size integers, "
            "for example 24,24,24,72;1,1,1,2."
        )
    return [
        ("lattice_size", " ".join(lattice_values)),
        ("grid_size", " ".join(grid_values)),
    ]


def _build_clover_solver_value_example(example_value_for_field: Callable[[str], str]) -> str:
    return ",".join(example_value_for_field(field_name) for field_name in CLOVER_SOLVER_PARAMETER_FIELDS)


def _build_lattice_geometry_value_example(example_value_for_field: Callable[[str], str]) -> str:
    lattice_example = example_value_for_field("lattice_size").replace(" ", ",")
    grid_example = example_value_for_field("grid_size").replace(" ", ",")
    return f"{lattice_example};{grid_example}"


GROUP_DEFINITIONS = [
    ClarificationGroupDefinition(
        group_id="clover_solver_parameters",
        label="clover solver parameters",
        fields=CLOVER_SOLVER_PARAMETER_FIELDS,
        parse_assignment=_parse_clover_solver_parameters,
        build_value_example=_build_clover_solver_value_example,
        supported_input_modes=("set",),
        recommended_input_mode="set",
    ),
    ClarificationGroupDefinition(
        group_id="lattice_geometry",
        label="lattice geometry",
        fields=LATTICE_GEOMETRY_FIELDS,
        parse_assignment=_parse_lattice_geometry,
        build_value_example=_build_lattice_geometry_value_example,
        supported_input_modes=("set",),
        recommended_input_mode="set",
    ),
]


FIELD_TO_GROUP: dict[str, ClarificationGroupDefinition] = {}
for definition in GROUP_DEFINITIONS:
    for field_name in definition.fields:
        FIELD_TO_GROUP[field_name] = definition


def expand_grouped_set_assignment(field_name: str, raw_value: str) -> list[tuple[str, str]] | None:
    for definition in GROUP_DEFINITIONS:
        if definition.group_id == field_name:
            return definition.parse_assignment(raw_value)
    return None


def build_group_metadata(
    *,
    batch_fields: list[str],
    example_value_for_field: Callable[[str], str],
    set_assignment_token: Callable[[str, str], str],
) -> list[dict]:
    field_groups: list[dict] = []
    for definition in GROUP_DEFINITIONS:
        present_fields = [field for field in definition.fields if field in batch_fields]
        if not present_fields:
            continue
        value_example = definition.build_value_example(example_value_for_field)
        field_groups.append(
            {
                "group_id": definition.group_id,
                "label": definition.label,
                "fields": present_fields,
                "complete_in_batch": present_fields == definition.fields,
                "partial_in_batch": present_fields != definition.fields,
                "value_example": value_example,
                "set_example": set_assignment_token(definition.group_id, value_example),
                "supported_input_modes": list(definition.supported_input_modes),
                "recommended_input_mode": definition.recommended_input_mode,
            }
        )

    return field_groups
