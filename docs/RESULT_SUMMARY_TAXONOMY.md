# Result Summary Taxonomy

`result_summary` is now a small product-facing contract for terminal users and thin UI clients.

Current identifiers:

- `schema_family = pyquda_agent.result_summary`
- `schema_version = 2026-07-v1`

The intent is:

- additive evolution within one schema version
- explicit version bumps when caller-visible state semantics change materially

## Stable top-level state

- `product_status`
  - `needs_input`
  - `ready_to_generate`
  - `generated_probe_available`
  - `generated_runtime_blocked`
  - `runtime_proved`
  - `unsupported`

## Stable blocked-state detail

- `blocking_reason_detail.category`
  - `needs_clarification`
  - `generation_not_emitted`
  - `unsupported_request`
  - `backend_fallback`
  - `backend_configuration_missing`
  - `backend_configuration_invalid`
  - `backend_credentials_missing`
  - `backend_local_executable_missing`
  - `backend_local_environment_error`
  - `backend_authentication_failed`
  - `backend_network_error`
  - `backend_timeout`
  - `backend_rate_limited`
  - `backend_service_unavailable`
  - `backend_endpoint_not_found`
  - `backend_request_error`
  - `backend_response_parse_error`
  - `backend_empty_response`
  - `backend_unexpected_error`
  - `backend_process_error`
  - `runtime_probe_not_run`
  - `runtime_dependencies_missing`
  - `runtime_probe_harness_failed`

`blocking_reason_detail.source` currently uses:

- `generation`
- `backend`
- `workflow_match`
- `runtime`

## Artifact guidance

- `inspection_hint.artifact_key`
  - `physics`
  - `task`
  - `plan`
  - `session`
  - `script`
  - `probe`

## Frontend profile

- `frontend_profile.status_card`
  - `product_status`
  - `headline`
  - `detail`
  - `blocking_kind`
  - `blocking_reason`
  - `blocking_reason_category`
- `frontend_profile.capabilities`
  - `backend_state`
  - `generation_state`
  - `runtime_state`
  - `runtime_proved`
- `frontend_profile.next`
  - `action_kind`
  - `action_title`
  - `actionable`
  - `command`
- `frontend_profile.inspect`
  - mirrors the current `inspection_hint`

## Thin result cards

- `generation_result`
  - `phase`
  - `headline`
  - `ready`
  - `emitted`
  - `succeeded`
  - `script_path`
  - `script_exists`
- `execution_result`
  - `phase`
  - `headline`
  - `attempted`
  - `succeeded`
  - `runtime_probe_status`
  - `runtime_level`
  - `evidence_level`
  - `probe_available`
  - `blocked`
  - `probe_command`
  - `probe_artifact`
- `execution_closure`
  - `state`
  - `headline`
  - `generation_phase`
  - `execution_phase`
  - `runtime_category`
  - `backend_category`
  - `why`
  - `next_artifact`
  - `next_command_kind`
  - `next_command`
  - `probe_artifact`
  - `script_artifact`
  - `actionable`

The intent of `execution_closure` is to answer one product question directly: "what exact stage is this run in, and what should I do or inspect next?" without forcing the caller to merge `workflow_outcome`, `delivery_status`, and `runtime_diagnostic`.

This file documents the product-facing taxonomy only. Implementation details still live in `docs/TASK_SCHEMAS.md` and `docs/RUN_WORKFLOW.md`.
For the intended high-level field mapping across lifecycle states, see `docs/RESULT_SUMMARY_STATUS_MAPPING.md`.
For compact example payloads, see `docs/RESULT_SUMMARY_EXAMPLES.md`.
