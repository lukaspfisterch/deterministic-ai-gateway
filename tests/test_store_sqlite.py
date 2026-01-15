from __future__ import annotations

from pathlib import Path

import pytest

from dbl_gateway.store.sqlite import SQLiteStore


def _append_intent(store: SQLiteStore) -> None:
    store.append(
        kind="INTENT",
        thread_id="t-1",
        turn_id="turn-1",
        parent_turn_id=None,
        lane="default",
        actor="user",
        intent_type="chat",
        stream_id="default",
        correlation_id="c-1",
        payload={"message": "hello"},
    )


def test_snapshot_round_trip_payload_json(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "trail.sqlite")
    _append_intent(store)

    snapshot = store.snapshot(limit=10, offset=0)
    assert snapshot["length"] == 1
    assert snapshot["events"][0]["payload"] == {"message": "hello"}

    payload_json = store._conn.execute("SELECT payload_json FROM events WHERE idx = 1").fetchone()[0]
    assert isinstance(payload_json, str)
    assert payload_json.startswith("{")


def test_append_rejects_invalid_payload_type(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "trail.sqlite")
    with pytest.raises(TypeError):
        store.append(
            kind="INTENT",
            thread_id="t-1",
            turn_id="turn-1",
            parent_turn_id=None,
            lane="default",
            actor="user",
            intent_type="chat",
            stream_id="default",
            correlation_id="c-1",
            payload="chat.message",  # type: ignore[arg-type]
        )
