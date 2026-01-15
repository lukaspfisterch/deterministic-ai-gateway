from __future__ import annotations

import sys
from pathlib import Path

import pytest


# Ensure test-local policy modules (e.g., policy_stub) are importable.
TESTS_DIR = Path(__file__).parent.resolve()
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))


@pytest.fixture(autouse=True)
def _default_policy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DBL_GATEWAY_POLICY_MODULE", "policy_stub")
    monkeypatch.setenv("DBL_GATEWAY_POLICY_OBJECT", "policy")
