"""Remember which graph step a call is on.

Redis keeps the step across guard processes. If Redis is down, the step stays
in this process so a single call can still move forward.
"""

from __future__ import annotations

import json
import os

_TTL = 60 * 60
_memory: dict[str, str] = {}
_redis = None
_redis_failed = False


def _client():
    global _redis, _redis_failed
    if _redis_failed:
        return None
    if _redis is not None:
        return _redis
    url = (os.environ.get("REDIS_URL") or "").strip()
    if not url:
        _redis_failed = True
        return None
    try:
        import redis.asyncio as redis
    except ImportError:
        _redis_failed = True
        return None
    _redis = redis.from_url(url, decode_responses=True)
    return _redis


def _empty_record(start: str) -> dict:
    return {"step": start, "refusals": 0, "opened": False, "slots": {}, "appointment_id": ""}


async def load_record(call_id: str, start: str) -> dict:
    key = f"dialogue:{call_id}"
    client = _client()
    raw = None
    if client is not None and call_id:
        try:
            raw = await client.get(key)
        except Exception:
            raw = _memory.get(key)
    else:
        raw = _memory.get(key)
    if not raw:
        return _empty_record(start)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _empty_record(start)
    try:
        refusals = int(payload.get("refusals") or 0)
    except (TypeError, ValueError):
        refusals = 0
    slots = payload.get("slots") if isinstance(payload.get("slots"), dict) else {}
    return {
        "step": str(payload.get("step") or start),
        "refusals": refusals,
        "opened": bool(payload.get("opened")),
        "slots": slots,
        "appointment_id": str(payload.get("appointment_id") or ""),
    }


async def save_record(call_id: str, record: dict) -> None:
    if not call_id:
        return
    key = f"dialogue:{call_id}"
    payload = json.dumps(
        {
            "step": record.get("step") or "",
            "refusals": int(record.get("refusals") or 0),
            "opened": bool(record.get("opened")),
            "slots": record.get("slots") or {},
            "appointment_id": record.get("appointment_id") or "",
        }
    )
    _memory[key] = payload
    client = _client()
    if client is None:
        return
    try:
        await client.set(key, payload, ex=_TTL)
    except Exception:
        return


async def load_state(call_id: str, start: str) -> tuple[str, int, bool]:
    record = await load_record(call_id, start)
    return record["step"], record["refusals"], record["opened"]


async def save_state(call_id: str, step: str, refusals: int = 0, opened: bool = False) -> None:
    record = await load_record(call_id, step)
    record["step"] = step
    record["refusals"] = refusals
    record["opened"] = opened
    await save_record(call_id, record)
