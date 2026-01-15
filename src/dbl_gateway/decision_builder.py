from __future__ import annotations

from typing import Mapping, Sequence

from .ports.policy_port import DecisionResult

DEFAULT_CONTEXT_DIGEST = "sha256:" + ("0" * 64)

__all__ = ["DEFAULT_CONTEXT_DIGEST", "build_normative_decision"]


def build_normative_decision(
    decision: DecisionResult,
    *,
    context_digest: str | None,
    transforms: Sequence[Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Construct the normative decision payload used for digesting."""
    context_digest_value = context_digest or DEFAULT_CONTEXT_DIGEST
    policy_id = decision.policy_id or "unknown"
    policy_version = decision.policy_version or "unknown"
    reasons = [{"code": code} for code in (decision.reason_codes or [])]
    norm_transforms = [dict(t) for t in (transforms or [])]
    return {
        "policy": {
            "policy_id": policy_id,
            "policy_version": policy_version,
        },
        "context_digest": context_digest_value,
        "result": decision.decision,
        "reasons": reasons,
        "transforms": norm_transforms,
    }
