from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .boundary import admit_model_messages
from dbl_gateway.contracts import AssembledContext, ContextSpec, DeclaredRef, context_digest

__all__ = ["ContextArtifacts", "build_context"]

DEFAULT_SCHEMA_VERSION = "ctxspec.1"
DEFAULT_ORDERING = "CANONICAL_V1"


@dataclass(frozen=True)
class ContextArtifacts:
    context_spec: ContextSpec
    assembled_context: AssembledContext
    context_digest: str
    boundary_meta: Mapping[str, Any] | None = None
    transforms: list[dict[str, Any]] = field(default_factory=list)


def build_context(payload: Mapping[str, Any] | None, *, intent_type: str) -> ContextArtifacts:
    """Deterministic assembly of ContextSpec, AssembledContext, and digest."""
    if not isinstance(intent_type, str) or not intent_type.strip():
        raise ValueError("intent_type is required to build context")
    payload_obj: Mapping[str, Any] = payload if isinstance(payload, Mapping) else {}

    user_input = _extract_user_input(payload_obj)
    identity = _extract_identity(payload_obj)
    declared_refs = _extract_declared_refs(payload_obj)

    context_spec: ContextSpec = {
        "identity": identity,
        "intent": {
            "intent_type": intent_type.strip(),
            "user_input": user_input,
        },
        "retrieval": {"declared_refs": declared_refs},
        "assembly_rules": {
            "schema_version": DEFAULT_SCHEMA_VERSION,
            "ordering": DEFAULT_ORDERING,
        },
    }

    raw_model_messages = _build_model_messages(user_input)
    admitted_model_messages, boundary_meta = admit_model_messages(raw_model_messages)
    transforms = _boundary_transforms(raw_model_messages, admitted_model_messages, boundary_meta)
    assembled_context: AssembledContext = {
        "model_messages": admitted_model_messages,
        "assembled_from": declared_refs,
    }
    context_digest_value = context_digest(context_spec, assembled_context)
    return ContextArtifacts(
        context_spec=context_spec,
        assembled_context=assembled_context,
        context_digest=context_digest_value,
        boundary_meta=boundary_meta,
        transforms=transforms,
    )


def _extract_identity(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    thread_id = payload.get("thread_id")
    turn_id = payload.get("turn_id")
    parent_turn_id = payload.get("parent_turn_id")
    if not isinstance(thread_id, str) or not thread_id.strip():
        raise ValueError("thread_id is required for context assembly")
    if not isinstance(turn_id, str) or not turn_id.strip():
        raise ValueError("turn_id is required for context assembly")
    parent_value = parent_turn_id if parent_turn_id is None else str(parent_turn_id)
    return {
        "thread_id": thread_id.strip(),
        "turn_id": turn_id.strip(),
        "parent_turn_id": parent_value if parent_value is None else str(parent_value),
    }


def _extract_user_input(payload: Mapping[str, Any]) -> str:
    message = payload.get("message")
    if not isinstance(message, str):
        raise ValueError("payload.message must be a string")
    user_input = message.strip()
    if not user_input:
        raise ValueError("payload.message must not be empty")
    return user_input


def _extract_declared_refs(payload: Mapping[str, Any]) -> list[DeclaredRef]:
    refs = payload.get("declared_refs")
    if not isinstance(refs, Sequence):
        return []
    normalized: list[DeclaredRef] = []
    for item in refs:
        if not isinstance(item, Mapping):
            continue
        ref_type = item.get("ref_type")
        ref_id = item.get("ref_id")
        version = item.get("version")
        if not isinstance(ref_type, str) or not ref_type.strip():
            continue
        if not isinstance(ref_id, str) or not ref_id.strip():
            continue
        ref: DeclaredRef = {"ref_type": ref_type.strip(), "ref_id": ref_id.strip()}
        if version is not None:
            ref["version"] = str(version)
        normalized.append(ref)
    normalized.sort(key=lambda r: (r["ref_type"], r["ref_id"], r.get("version") or ""))
    return normalized


def _build_model_messages(user_input: str) -> list[dict[str, str]]:
    return [{"role": "user", "content": user_input}]


def _boundary_transforms(
    raw_messages: Sequence[Mapping[str, Any]],
    admitted_messages: Sequence[Mapping[str, Any]],
    boundary_meta: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    transforms: list[dict[str, Any]] = []
    rejections = []
    if isinstance(boundary_meta, Mapping):
        rejections = boundary_meta.get("rejections") or []
    if isinstance(rejections, list):
        for item in rejections:
            if not isinstance(item, Mapping):
                continue
            idx = item.get("index")
            reason = item.get("reason")
            if not isinstance(idx, int):
                continue
            transform: dict[str, Any] = {
                "op": "DROP_MESSAGE",
                "target": f"model_messages[{idx}]",
            }
            if isinstance(reason, str) and reason.strip():
                transform["params"] = {"reason": reason.strip()}
            transforms.append(transform)

    # If no drops but boundary normalized content, record that normalization occurred.
    if len(raw_messages) == len(admitted_messages):
        for idx, (raw_msg, admitted) in enumerate(zip(raw_messages, admitted_messages)):
            if _normalized_message(raw_msg) != _normalized_message(admitted):
                transforms.append(
                    {
                        "op": "NORMALIZE_MESSAGE",
                        "target": f"model_messages[{idx}]",
                        "params": {"reason": "boundary.normalized"},
                    }
                )
    return transforms


def _normalized_message(value: Mapping[str, Any]) -> Mapping[str, str]:
    role = value.get("role")
    content = value.get("content")
    return {
        "role": role.strip() if isinstance(role, str) else "",
        "content": content.strip() if isinstance(content, str) else "",
    }
