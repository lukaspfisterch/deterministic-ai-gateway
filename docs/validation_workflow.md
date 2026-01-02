# Validate a DBL system against dbl-reference

Goal: validate invariants and replay equivalence of your event stream against the
reference oracle.

## Inputs
Export your system event stream as JSONL:
- One JSON object per line.
- Required keys: `event_id`, `kind`, `correlation_id`, `payload`.

## Validate invariants
```bash
cat events.jsonl | dbl-reference --mode validate
```

- Exit code 0: OK.
- Non-zero: invariant or replay failure (see stderr).

## Replay projection
```bash
cat events.jsonl | dbl-reference --mode replay
```

## Normative digest
```bash
cat events.jsonl | dbl-reference --mode validate --digest
cat events.jsonl | dbl-reference --mode replay --digest
```

Compare digests across systems to assert normative equivalence.

Example input:

```json
{"event_id":1,"kind":"INTENT","correlation_id":"c1","payload":{"authoritative_input":{"x":1},"policy_version":1}}
{"event_id":2,"kind":"DECISION","correlation_id":"c1","payload":{"decision":"ALLOW","policy_version":1,"authoritative_digest":"sha256:..."}}
{"event_id":3,"kind":"EXECUTION","correlation_id":"c1","payload":{"output":"ok","latency_ms":12}}
```

PowerShell helper:

```powershell
param(
  [Parameter(Mandatory=$true)][string]$Path
)

Get-Content $Path | dbl-reference --mode validate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Get-Content $Path | dbl-reference --mode validate --digest
```

