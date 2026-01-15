from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import uuid
from pathlib import Path

import httpx

from dbl_gateway.app import create_app


def _prepare_env(tmp_db: Path) -> None:
    # Use the test policy for deterministic decisions.
    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    sys.path.insert(0, str(tests_dir))
    os.environ.setdefault("DBL_GATEWAY_POLICY_MODULE", "policy_stub")
    os.environ.setdefault("DBL_GATEWAY_POLICY_OBJECT", "policy")
    os.environ.setdefault("DBL_GATEWAY_DB", str(tmp_db))
    os.environ.setdefault("GATEWAY_EXEC_MODE", "external")


async def _run_demo() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "trail.sqlite"
        _prepare_env(db_path)
        app = create_app(start_workers=True)
        thread_id = f"demo-{uuid.uuid4().hex[:8]}"

        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://demo") as client:
                await _post_intent(client, thread_id, "turn-1", None)
                await _post_intent(client, thread_id, "turn-2", "turn-1")
                await _post_intent(client, thread_id, "turn-3a", "turn-1")
                await _wait_for_decisions(client, expected=3)

                timeline = (await client.get(f"/threads/{thread_id}/timeline")).json()
                _print_timeline(timeline)


async def _post_intent(
    client: httpx.AsyncClient,
    thread_id: str,
    turn_id: str,
    parent_turn_id: str | None,
) -> None:
    envelope = {
        "interface_version": 1,
        "correlation_id": uuid.uuid4().hex,
        "payload": {
            "stream_id": "default",
            "lane": "demo",
            "actor": "demo-user",
            "intent_type": "chat.message",
            "thread_id": thread_id,
            "turn_id": turn_id,
            "parent_turn_id": parent_turn_id,
            "payload": {"message": f"hello from {turn_id}"},
        },
    }
    resp = await client.post("/ingress/intent", json=envelope)
    resp.raise_for_status()


async def _wait_for_decisions(client: httpx.AsyncClient, expected: int) -> None:
    for _ in range(40):
        snap = (await client.get("/snapshot")).json()
        decisions = [event for event in snap.get("events", []) if event.get("kind") == "DECISION"]
        if len(decisions) >= expected:
            return
        await asyncio.sleep(0.05)
    raise RuntimeError("DECISION events not emitted")


def _print_timeline(timeline: dict[str, object]) -> None:
    print(f"Thread: {timeline.get('thread_id')}")
    turns = timeline.get("turns") or []
    for turn in turns:
        turn_id = turn.get("turn_id")
        parent = turn.get("parent_turn_id")
        decisions = [e for e in turn.get("events", []) if e.get("kind") == "DECISION"]
        ctx = decisions[-1].get("context_digest") if decisions else None
        dec = decisions[-1].get("decision_digest") if decisions else None
        print(f"- turn: {turn_id}, parent: {parent}, context_digest: {ctx}, decision_digest: {dec}")


def main() -> None:
    asyncio.run(_run_demo())


if __name__ == "__main__":
    main()
