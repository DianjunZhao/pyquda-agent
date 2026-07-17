# Result Summary Examples

This note shows a few compact `result_summary` shapes for product-style consumers.

## Needs input with backend fallback

```json
{
  "product_status": "needs_input",
  "generation_result": {
    "phase": "blocked_on_input",
    "ready": false,
    "emitted": false
  },
  "execution_result": {
    "phase": "blocked_by_generation",
    "attempted": false,
    "probe_available": false
  },
  "blocking_reason_detail": {
    "category": "backend_fallback",
    "source": "backend"
  }
}
```

## Script generated, probe available

```json
{
  "product_status": "generated_probe_available",
  "generation_result": {
    "phase": "generated",
    "ready": true,
    "emitted": true,
    "script_exists": true
  },
  "execution_result": {
    "phase": "probe_available",
    "attempted": false,
    "probe_available": true,
    "probe_command": "python3 scripts/probe_generated_workflow.py ..."
  }
}
```

## Script generated, runtime blocked

```json
{
  "product_status": "generated_runtime_blocked",
  "generation_result": {
    "phase": "generated",
    "emitted": true
  },
  "execution_result": {
    "phase": "runtime_missing",
    "attempted": true,
    "blocked": true,
    "runtime_level": "environment_missing"
  },
  "blocking_reason_detail": {
    "category": "runtime_dependencies_missing",
    "source": "runtime"
  }
}
```

## Runtime proved

```json
{
  "product_status": "runtime_proved",
  "generation_result": {
    "phase": "generated",
    "emitted": true
  },
  "execution_result": {
    "phase": "runtime_proved",
    "attempted": true,
    "succeeded": true
  }
}
```

## Unsupported request

```json
{
  "product_status": "unsupported",
  "generation_result": {
    "phase": "unsupported",
    "ready": false
  },
  "execution_result": {
    "phase": "unsupported",
    "attempted": false
  },
  "blocking_reason_detail": {
    "category": "unsupported_request",
    "source": "workflow_match"
  }
}
```

Use these fields as a convenience layer. The authoritative detailed state still lives in:

- `workflow_outcome`
- `delivery_status`
- `backend_diagnostic`
- `runtime_diagnostic`
