# Result Summary Status Mapping

This note records the intended high-level relationship among:

- `product_status`
- `delivery_status.generation.phase`
- `delivery_status.execution.phase`
- `generation_result.phase`
- `execution_result.phase`
- `run_overview.blocking_kind`
- `blocking_reason_detail.category`

for the current `result_summary` contract family.

## Common mappings

| Scenario | `product_status` | `generation.phase` | `execution.phase` | `generation_result.phase` | `execution_result.phase` | `blocking_kind` | `blocking_reason_detail.category` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Clarification still needed, no specific backend subtype | `needs_input` | `blocked_on_input` | `blocked_by_generation` | `blocked_on_input` | `blocked_by_generation` | `backend_fallback` or `clarification` | `backend_fallback` or `needs_clarification` |
| Dry-run ready, no script emitted yet | `ready_to_generate` | `ready_to_generate` | `blocked_by_generation` | `ready_to_generate` | `blocked_by_generation` | `generation` or `backend_fallback` | `generation_not_emitted` or a backend fallback subtype |
| Script generated, probe not run | `generated_probe_available` | `generated` | `probe_available` | `generated` | `probe_available` | `runtime_probe_optional` | `runtime_probe_not_run` |
| Script generated, runtime environment missing pieces | `generated_runtime_blocked` | `generated` | `runtime_missing` | `generated` | `runtime_missing` | `runtime_environment` | `runtime_dependencies_missing` |
| Script generated, probe harness failed | `generated_runtime_blocked` | `generated` | `probe_driver_failed` | `generated` | `probe_driver_failed` | `probe_driver` | `runtime_probe_harness_failed` |
| Script generated, runtime proof succeeded | `runtime_proved` | `generated` | `runtime_proved` | `generated` | `runtime_proved` | `none` | `null` |
| Confirmed request unsupported | `unsupported` | `unsupported` | `unsupported` | `unsupported` | `unsupported` | `unsupported` | `unsupported_request` |

## Important precedence notes

- Backend fallback can override the more generic `clarification` or `generation` blocking kind in `run_overview` when the run is still otherwise actionable.
- `delivery_status` stays focused on generation/execution lifecycle, while `run_overview.blocking_kind` is allowed to surface a more product-facing dominant blocker.
- `blocking_reason_detail.category` is expected to be the most specific structured blocker available for the current summary; when no subtype is available it may intentionally stay broad, such as `backend_fallback`.
- Before script generation succeeds, runtime evidence should stay at `structurally_grounded`; `environment_missing` and other runtime-failure classes are reserved for runs that actually emitted a script and attempted or analyzed runtime proof.

For the versioned vocabulary itself, see `docs/RESULT_SUMMARY_TAXONOMY.md`.
