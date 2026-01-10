from __future__ import annotations

from typing import Any, Mapping

from dbl_core.events.canonical import canonicalize_value, digest_bytes, json_dumps

__all__ = ["build_context"]


def build_context(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Pure, deterministic assembly of model_messages and context_digest."""
    model_messages: list[dict[str, str]] = []
    if isinstance(payload, Mapping):
        message = payload.get("message")
        if isinstance(message, str):
            text = message.strip()
            if text:
                model_messages.append({"role": "user", "content": text})

    canonical = canonicalize_value(model_messages)
    digest = digest_bytes(json_dumps(canonical))
    if not digest.startswith("sha256:"):
        digest = f"sha256:{digest}"
    return {"model_messages": model_messages, "context_digest": digest}
