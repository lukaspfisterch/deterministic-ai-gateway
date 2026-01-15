from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, TypedDict

from dbl_core.events.canonical import canonicalize_value, json_dumps


# Event envelope with mandatory identity anchors.
class EventEnvelope(TypedDict, total=False):
    kind: str
    thread_id: str
    turn_id: str
    parent_turn_id: str | None
    correlation_id: str
    payload: dict[str, Any]
    _obs: dict[str, Any]


class PolicyIdent(TypedDict):
    policy_id: str
    policy_version: str


class DecisionReason(TypedDict, total=False):
    code: str
    params: Mapping[str, Any]


class DecisionTransform(TypedDict, total=False):
    op: str
    target: str
    params: Mapping[str, Any]


class DecisionNormative(TypedDict):
    policy: PolicyIdent
    context_digest: str
    result: str
    reasons: list[DecisionReason]
    transforms: list[DecisionTransform]


class ContextIdentity(TypedDict, total=False):
    thread_id: str
    turn_id: str
    parent_turn_id: str | None


class IntentSpec(TypedDict):
    intent_type: str
    user_input: str


class DeclaredRef(TypedDict, total=False):
    ref_type: str
    ref_id: str
    version: str | None


class RetrievalSpec(TypedDict):
    declared_refs: list[DeclaredRef]


class AssemblyRules(TypedDict, total=False):
    schema_version: str
    ordering: str
    limits: Mapping[str, Any]


class ContextSpec(TypedDict):
    identity: ContextIdentity
    intent: IntentSpec
    retrieval: RetrievalSpec
    assembly_rules: AssemblyRules


class AssembledContext(TypedDict, total=False):
    model_messages: list[dict[str, Any]]
    assembled_from: list[DeclaredRef]
    warnings: list[str]


def canonical_json(value: Any) -> str:
    return canonical_json_bytes(value).decode("utf-8")


def canonical_json_bytes(value: Any) -> bytes:
    """
    Canonical JSON: sorted keys, stable separators, UTF-8 bytes, NaN/Infinity rejected,
    non-JSON types rejected via canonicalize_value.
    """
    canonical = canonicalize_value(value)
    return json_dumps(canonical).encode("utf-8")


def normalize_sha256_hex(value: str) -> str:
    return value if value.startswith("sha256:") else f"sha256:{value}"


def decision_digest(decision: Mapping[str, Any]) -> str:
    # Only normative fields count toward the digest.
    required_fields = {"policy", "context_digest", "result", "reasons", "transforms"}
    missing = [f for f in required_fields if f not in decision]
    if missing:
        raise ValueError(f"DecisionNormative missing fields: {', '.join(missing)}")
    filtered = _strip_obs(decision)
    normative = _normalize_decision(filtered)
    canonical_bytes = canonical_json_bytes(normative)
    return normalize_sha256_hex(_sha256_hex(canonical_bytes))


def context_digest(spec: Mapping[str, Any], assembled: Mapping[str, Any]) -> str:
    normalized_spec = _normalize_context_spec(_strip_obs(spec))
    normalized_assembled = _normalize_assembled_context(_strip_obs(assembled))
    payload = {"context_spec": normalized_spec, "assembled_context": normalized_assembled}
    canonical_bytes = canonical_json_bytes(payload)
    return normalize_sha256_hex(_sha256_hex(canonical_bytes))


def canonical_json_without_obs(value: Mapping[str, Any]) -> str:
    if "_obs" in value:
        filtered = dict(value)
        filtered.pop("_obs", None)
    else:
        filtered = value
    canonical = canonicalize_value(filtered)
    return json_dumps(canonical)


def _sha256_hex(data: bytes) -> str:
    return sha256(data).hexdigest()


@dataclass(frozen=True)
class DecisionDigests:
    decision_digest: str
    canonical_json: str


def _strip_obs(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if "_obs" not in value:
        return value
    filtered = dict(value)
    filtered.pop("_obs", None)
    return filtered


def _normalize_decision(decision: Mapping[str, Any]) -> DecisionNormative:
    policy = decision.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("policy must be an object with policy_id and policy_version")
    policy_id = policy.get("policy_id")
    policy_version = policy.get("policy_version")
    if not isinstance(policy_id, str) or not policy_id.strip():
        raise ValueError("policy.policy_id must be a non-empty string")
    if not isinstance(policy_version, str) or not policy_version.strip():
        raise ValueError("policy.policy_version must be a non-empty string")
    context_digest_value = decision.get("context_digest")
    if not isinstance(context_digest_value, str) or not context_digest_value.strip():
        raise ValueError("context_digest must be a non-empty string")
    result = decision.get("result")
    if result not in ("ALLOW", "DENY"):
        raise ValueError("result must be ALLOW or DENY")

    reasons_raw = decision.get("reasons") or []
    if not isinstance(reasons_raw, list):
        raise ValueError("reasons must be a list")
    norm_reasons: list[DecisionReason] = []
    for item in reasons_raw:
        if not isinstance(item, Mapping):
            raise ValueError("reason entries must be objects")
        code = item.get("code")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("reason.code must be a non-empty string")
        reason: DecisionReason = {"code": code.strip()}
        params = item.get("params")
        if params is not None:
            if not isinstance(params, Mapping):
                raise ValueError("reason.params must be an object")
            reason["params"] = dict(params)
        norm_reasons.append(reason)
    # Canonical ordering for digest determinism.
    norm_reasons.sort(key=lambda r: (r["code"], json_dumps(canonicalize_value(r.get("params", {})))))

    transforms_raw = decision.get("transforms") or []
    if not isinstance(transforms_raw, list):
        raise ValueError("transforms must be a list")
    norm_transforms: list[DecisionTransform] = []
    for item in transforms_raw:
        if not isinstance(item, Mapping):
            raise ValueError("transform entries must be objects")
        op = item.get("op")
        target = item.get("target")
        if not isinstance(op, str) or not op.strip():
            raise ValueError("transform.op must be a non-empty string")
        if not isinstance(target, str) or not target.strip():
            raise ValueError("transform.target must be a non-empty string")
        transform: DecisionTransform = {"op": op.strip(), "target": target.strip()}
        params = item.get("params")
        if params is not None:
            if not isinstance(params, Mapping):
                raise ValueError("transform.params must be an object")
            transform["params"] = dict(params)
        norm_transforms.append(transform)
    # Canonical ordering for digest determinism.
    norm_transforms.sort(
        key=lambda t: (t["op"], t["target"], json_dumps(canonicalize_value(t.get("params", {})))))

    return {
        "policy": {"policy_id": policy_id.strip(), "policy_version": policy_version.strip()},
        "context_digest": context_digest_value.strip(),
        "result": result,
        "reasons": norm_reasons,
        "transforms": norm_transforms,
    }


def _normalize_declared_refs(refs: list[Mapping[str, Any]]) -> list[DeclaredRef]:
    normalized: list[DeclaredRef] = []
    for item in refs:
        if not isinstance(item, Mapping):
            raise ValueError("declared_refs entries must be objects")
        ref_type = item.get("ref_type")
        ref_id = item.get("ref_id")
        version = item.get("version")
        if not isinstance(ref_type, str) or not ref_type.strip():
            raise ValueError("ref_type must be a non-empty string")
        if not isinstance(ref_id, str) or not ref_id.strip():
            raise ValueError("ref_id must be a non-empty string")
        norm: DeclaredRef = {"ref_type": ref_type.strip(), "ref_id": ref_id.strip()}
        if version is not None:
            norm["version"] = str(version)
        normalized.append(norm)
    normalized.sort(key=lambda r: (r["ref_type"], r["ref_id"], r.get("version") or ""))
    return normalized


def _normalize_context_spec(spec: Mapping[str, Any]) -> ContextSpec:
    identity = spec.get("identity")
    intent = spec.get("intent")
    retrieval = spec.get("retrieval")
    rules = spec.get("assembly_rules")
    if not isinstance(identity, Mapping):
        raise ValueError("identity must be an object")
    if not isinstance(intent, Mapping):
        raise ValueError("intent must be an object")
    if not isinstance(retrieval, Mapping):
        raise ValueError("retrieval must be an object")
    if not isinstance(rules, Mapping):
        raise ValueError("assembly_rules must be an object")

    declared_refs_raw = retrieval.get("declared_refs") or []
    if not isinstance(declared_refs_raw, list):
        raise ValueError("declared_refs must be a list")
    declared_refs = _normalize_declared_refs(declared_refs_raw)

    thread_id = identity.get("thread_id")
    turn_id = identity.get("turn_id")
    parent_turn_id = identity.get("parent_turn_id")
    if not isinstance(thread_id, str) or not thread_id.strip():
        raise ValueError("identity.thread_id must be a non-empty string")
    if not isinstance(turn_id, str) or not turn_id.strip():
        raise ValueError("identity.turn_id must be a non-empty string")
    intent_type = intent.get("intent_type")
    user_input = intent.get("user_input")
    if not isinstance(intent_type, str) or not intent_type.strip():
        raise ValueError("intent.intent_type must be a non-empty string")
    if not isinstance(user_input, str) or not user_input.strip():
        raise ValueError("intent.user_input must be a non-empty string")

    schema_version = rules.get("schema_version")
    ordering = rules.get("ordering")
    if not isinstance(schema_version, str) or not schema_version.strip():
        raise ValueError("assembly_rules.schema_version must be a non-empty string")
    if not isinstance(ordering, str) or not ordering.strip():
        raise ValueError("assembly_rules.ordering must be a non-empty string")

    normalized: ContextSpec = {
        "identity": {
            "thread_id": thread_id.strip(),
            "turn_id": turn_id.strip(),
            "parent_turn_id": parent_turn_id if parent_turn_id is None else str(parent_turn_id),
        },
        "intent": {
            "intent_type": intent_type.strip(),
            "user_input": user_input,
        },
        "retrieval": {"declared_refs": declared_refs},
        "assembly_rules": {
            "schema_version": schema_version.strip(),
            "ordering": ordering.strip(),
        },
    }
    limits = rules.get("limits")
    if limits is not None:
        if not isinstance(limits, Mapping):
            raise ValueError("assembly_rules.limits must be an object when provided")
        normalized["assembly_rules"]["limits"] = dict(limits)
    return normalized


def _normalize_assembled_context(assembled: Mapping[str, Any]) -> AssembledContext:
    model_messages = assembled.get("model_messages")
    assembled_from = assembled.get("assembled_from") or []
    warnings = assembled.get("warnings")
    if model_messages is None:
        model_messages = []
    if not isinstance(model_messages, list):
        raise ValueError("assembled_context.model_messages must be a list")
    if not isinstance(assembled_from, list):
        raise ValueError("assembled_context.assembled_from must be a list")
    normalized_from = _normalize_declared_refs(assembled_from)
    normalized: AssembledContext = {
        "model_messages": list(model_messages),
        "assembled_from": normalized_from,
    }
    if warnings is not None:
        if not isinstance(warnings, list):
            raise ValueError("assembled_context.warnings must be a list when provided")
        normalized["warnings"] = list(warnings)
    return normalized
