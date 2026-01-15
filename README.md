# Deterministic AI Gateway

Execution boundary for LLM calls.

This project turns AI usage into a deterministic, auditable event chain with explicit boundaries.
It is not an agent framework, not a RAG framework, and not a UI product.

## Core idea

Every AI call is a canonical chain:

1. INTENT
2. CONTEXT (deterministic assembly, produces `context_digest`)
3. ADMISSION (boundary decisions: what may enter / what may leave)
4. EXECUTION
5. DECISION (records output + meta)

## Canonized usage

### Required identity anchors
Each INTENT must include:
- `thread_id` (stable across a dialog or workflow)
- `turn_id` (unique per call)
- `parent_turn_id` (optional, enables branching)

### Deterministic context
Context assembly is a pure function:
- same inputs -> same `model_messages`
- `context_digest = sha256(canonical(model_messages))`
- digest is echoed into DECISION

### Boundaries
Boundaries are deterministic decisions, not heuristics:
- Input admission: which context chunks may enter the model input
- Context authority: whether a source is binding vs advisory vs volatile
- Output scope: what may be emitted under policy

## Non-goals
- Agent orchestration and planning
- Vector databases, indexing, embedding pipelines
- UI/UX layers
- Reconstructing application state from events
- Explaining policies to end users

## Thread timeline and replay
- Timeline endpoint: `GET /threads/{thread_id}/timeline` lists turns and event digests in deterministic order.
- Parent rules: each `parent_turn_id`, when present, must exist in the same thread, cannot equal `turn_id`, and cycles are rejected.
- DECISION artifacts are replayable offline using stored context_spec/assembled_context and the recorded policy identity.

## Status
Early, moving fast. Canon and invariants first.

## License
TBD
