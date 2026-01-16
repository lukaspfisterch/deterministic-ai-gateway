# AI Gateway

![Tests](https://github.com/lukaspfisterch/deterministic-ai-gateway/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/github/license/lukaspfisterch/deterministic-ai-gateway)

This repository provides a **controlled execution boundary for LLM calls**.

It separates *request*, *decision*, and *execution* into an explicit, inspectable flow and records every interaction as an append-only event stream.

The goal is not autonomy or orchestration, but **traceability, control, and replayability**.

This is **not**:
- an agent framework
- a RAG system
- a UI product

It is infrastructure for running LLM calls in a way that remains observable and explainable over time.

---

## Repository Landscape

The gateway is part of a small toolchain:

### deterministic-ai-gateway (this repository)
Authoritative execution boundary and event log.
- Accepts explicit intents.
- Applies policy.
- Executes provider calls.
- Emits canonical events (`INTENT`, `DECISION`, `EXECUTION`).
- Persists an append-only event trail.
- Exposes read-only observation surfaces (`/snapshot`, `/tail`).

### [dbl-operator](https://github.com/lukaspfisterch/dbl-operator)
Observer and intervention client. Used for rendering timelines, audits, and decision views. Does not evaluate policy or store authoritative state.

### [dbl-chat-cli](https://github.com/lukaspfisterch/dbl-chat-cli)
Minimal interactive CLI client for smoke testing and quick interaction via terminal.

### [dbl-chat-client](https://github.com/lukaspfisterch/dbl-chat-client)
Pure event-projection UI. Real-time visualization of the gateway event stream and identity anchor management.

---

## Interaction Model

Every interaction follows the same sequence:

1. **INTENT** – explicit request with identity anchors (`thread_id`, `turn_id`).
2. **DECISION** – policy outcome (ALLOW/DENY).
3. **EXECUTION** – provider call and result.
4. **OBSERVATION** – read-only access via snapshot or tail.

No step is implicit; every event is linked via a stable `correlation_id`.

---

## Design Principles

- **Explicit boundaries**: Strict separation between core logic, policy, and execution.
- **Append-only records**: Immutable event trail for audit and replay.
- **No hidden state**: No heuristics or internal memory beyond the event stream.
- **Observer-safe**: Clients observe and project state; the gateway makes normative decisions.

---

## Installation

### Local Install
Create a virtual environment and install the gateway:
```bash
pip install .
```

### Docker
Run the gateway via Docker:
```bash
docker build -t dbl-gateway .
docker run -p 8010:8010 \
  -e OPENAI_API_KEY="sk-..." \
  -e DBL_GATEWAY_POLICY_MODULE="dbl_policy.allow_all" \
  dbl-gateway
```

---

## Running the Gateway

### Required Environment Variables

| Variable | Description |
| :--- | :--- |
| `OPENAI_API_KEY` | Provider API key. |
| `DBL_GATEWAY_POLICY_MODULE` | Policy module (e.g., `dbl_policy.allow_all`). |
| `DBL_GATEWAY_POLICY_OBJECT` | Policy object inside the module (default: `policy`). |

### Start Command
```bash
dbl-gateway serve --host 127.0.0.1 --port 8010
```

---

## Observation Surfaces

### Snapshot (`/snapshot`)
Returns a point-in-time state of the event log. Suitable for audits and offline inspection.

### Tail (`/tail`)
A live SSE stream of events. 
- `since`: Start streaming from a specific event index.
- `backlog`: Number of recent events to emit on connect (default: 20).

---

## Integration Examples

### Using the [Operator](https://github.com/lukaspfisterch/dbl-operator)
```powershell
$env:DBL_GATEWAY_BASE_URL = "http://127.0.0.1:8010"
dbl-operator thread-view --thread-id t-1
```

### Using the [Chat CLI](https://github.com/lukaspfisterch/dbl-chat-cli)
```powershell
dbl-chat-cli --base-url http://127.0.0.1:8010 --principal-id user-1
```

### Using the [Chat Client](https://github.com/lukaspfisterch/dbl-chat-client)
```powershell
# In the dbl-chat-client repository:
npm install && npm run dev
```

---

## Status
**Early but functional.** Core execution, policy gating, and auditing are operational. Current focus: surface stabilization and contract clarity.