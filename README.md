# Deterministic AI Gateway

The **Deterministic AI Gateway** is a secure execution boundary for LLM calls.

It turns AI usage into a deterministic, auditable event stream by enforcing strict separation between:
- **Intent**
- **Policy Decision**
- **Execution**
- **Observation**

It is **not** an agent framework, a RAG system, or a UI product. It is a governance and execution boundary.

---

## Repository Landscape

This project is part of a small, explicit toolchain:

### 1. [deterministic-ai-gateway](https://github.com/lukaspfisterch/deterministic-ai-gateway) (this repository)
**Role**: Authoritative execution boundary.

**Responsibilities**:
- Accepts intents.
- Applies policy.
- Executes LLM calls.
- Emits canonical events (`INTENT`, `DECISION`, `EXECUTION`).
- Persists an append-only event trail.
- Exposes observation surfaces (`/snapshot`, `/tail`).

*This is the only authoritative component.*

### 2. [dbl-operator](https://github.com/lukaspfisterch/dbl-operator)
**Role**: Observer + intervention client.

**Responsibilities**:
- Sends intents to the gateway.
- Observes gateway state via snapshot and tail.
- Renders timelines, audits, and decision views.
- **Does not** evaluate policy or compute digests.
- **Does not** store authoritative state.

*Think of it as a cockpit, not a brain.*

### 3. [dbl-chat-cli](https://github.com/lukaspfisterch/dbl-chat-cli)
**Role**: Minimal interactive client.

**Responsibilities**:
- Sends chat intents.
- Displays execution results.
- Useful for smoke testing and demos.

*Intentionally thin and non-authoritative.*

---

## Core Model

Every AI interaction produces a canonical event chain:

1. **INTENT**: Explicit request with identity anchors.
2. **DECISION**: Policy evaluation result (normative).
3. **EXECUTION**: Actual provider call and output.
4. **OBSERVATION**: Read-only access via snapshot or tail.

*No component may skip a step.*

---

## Identity Anchors

Every intent must include:
- **`thread_id`**: Stable identifier for a conversation or workflow.
- **`turn_id`**: Unique identifier for this call.
- **`parent_turn_id`** (optional): Enables branching and causal structure.

*These anchors are supplied by the caller, not invented by the gateway.*

---

## Design Stance

- **Deterministic**: Same inputs produce the same digests.
- **Auditable**: All decisions are append-only and replayable.
- **Explicit boundaries**: No heuristics, no hidden state.
- **Observer-safe**: Clients may observe, never decide.

---

## Installation

Create a virtual environment and install the gateway in editable mode:

```bash
pip install -e .
```

---

## Running the Gateway

### Required Environment Variables

| Variable | Description |
| :--- | :--- |
| `OPENAI_API_KEY` | Provider API key. |
| `DBL_GATEWAY_POLICY_MODULE` | Policy module (e.g., `dbl_policy.allow_all`). |
| `DBL_GATEWAY_POLICY_OBJECT` | Policy object inside the module (usually `policy`). |

*The gateway will not start without a policy module.*

### Start (Bash / Zsh)
```bash
export OPENAI_API_KEY="sk-proj-..."
export DBL_GATEWAY_POLICY_MODULE="dbl_policy.allow_all"
export DBL_GATEWAY_POLICY_OBJECT="policy"

dbl-gateway serve --host 127.0.0.1 --port 8010
```

### Start (PowerShell)
```powershell
$env:OPENAI_API_KEY = "sk-proj-..."
$env:DBL_GATEWAY_POLICY_MODULE = "dbl_policy.allow_all"
$env:DBL_GATEWAY_POLICY_OBJECT = "policy"

dbl-gateway serve --host 127.0.0.1 --port 8010
```

> **Note**: Use `$env:VAR = "value"` for the current session. `setx` only applies to new terminals.

---

## Observation Surfaces

### Snapshot (`/snapshot`)
- **Finite**: Returns a point-in-time state.
- **Usage**: Used for audits and historical inspection.
- **Target**: Suitable for tools and offline analysis.

### Tail (`/tail`)
The `/tail` endpoint is a **live stream**, not a log dump.

- **Default behavior**: On connect, the gateway emits only the last 20 events, then continues live.
- **Query parameters**:
  - `since`: Start streaming from a specific event index.
  - `backlog`: Number of recent events to emit on connect (only applied if `since` is omitted, default = 20).

#### Examples (Bash)
```bash
# Live tail (default: last 20 events)
curl -N http://127.0.0.1:8010/tail

# Live tail with explicit backlog
curl -N "http://127.0.0.1:8010/tail?backlog=50"

# Resume from a known cursor
curl -N "http://127.0.0.1:8010/tail?since=1234"
```

#### Examples (PowerShell)
```powershell
# Live tail (default)
curl.exe -N "http://127.0.0.1:8010/tail"

# Live tail with backlog
curl.exe -N "http://127.0.0.1:8010/tail?backlog=50"

# Resume from cursor
curl.exe -N "http://127.0.0.1:8010/tail?since=1234"
```

---

## Integration Examples

### Using the [Operator](https://github.com/lukaspfisterch/dbl-operator)
```powershell
$env:DBL_GATEWAY_BASE_URL = "http://127.0.0.1:8010"

# Send an intent
dbl-operator send-intent `
  --thread-id t-1 `
  --turn-id turn-1 `
  --intent-type PING `
  --correlation-id demo-1

# View results
dbl-operator thread-view --thread-id t-1
dbl-operator audit-view  --thread-id t-1
```

### Using the [Chat CLI](https://github.com/lukaspfisterch/dbl-chat-cli)
```powershell
dbl-chat-cli --base-url http://127.0.0.1:8010 --principal-id user-1
```

---

## Non-Goals
- Agent planning or orchestration.
- Memory systems or embeddings.
- Vector databases.
- UI frameworks.
- "Smart" behavior.

*This system optimizes for clarity, auditability, and control, not autonomy.*

---

## Status
**Early but functional.**
Core execution, policy gating, tailing, and auditing are operational. Current focus: surface stabilization and contract clarity.