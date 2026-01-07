from __future__ import annotations

from typing import Any, Mapping, Sequence

__all__ = ["admit_model_messages"]


def admit_model_messages(model_messages: Sequence[Mapping[str, Any]] | None) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Deterministic boundary admission for model_messages."""
    if model_messages is None:
        model_messages = []

    admitted: list[dict[str, str]] = []
    rejections: list[dict[str, object]] = []

    for idx, msg in enumerate(model_messages):
        if not isinstance(msg, Mapping):
            rejections.append({"index": idx, "reason": "shape.invalid"})
            continue
        raw_role = msg.get("role")
        raw_content = msg.get("content")
        if not isinstance(raw_role, str) or not raw_role.strip():
            rejections.append({"index": idx, "reason": "role.invalid"})
            continue
        if not isinstance(raw_content, str):
            rejections.append({"index": idx, "reason": "content.invalid_type"})
            continue
        content = raw_content.strip()
        if content == "":
            rejections.append({"index": idx, "reason": "content.empty"})
            continue
        admitted.append({"role": raw_role.strip(), "content": content})

    meta: dict[str, Any] = {
        "input_count": len(model_messages),
        "admitted_count": len(admitted),
        "decision": "ALLOW" if not rejections else "ALLOW_WITH_DROPS",
    }
    if rejections:
        meta["rejections"] = rejections
    return admitted, meta
