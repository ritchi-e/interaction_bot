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


async def load_state(call_id: str, start: str) -> tuple[str, int, bool]:
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
        return start, 0, False
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return start, 0, False
    try:
        refusals = int(payload.get("refusals") or 0)
    except (TypeError, ValueError):
        refusals = 0
    return str(payload.get("step") or start), refusals, bool(payload.get("opened"))


async def save_state(call_id: str, step: str, refusals: int = 0, opened: bool = False) -> None:
    if not call_id:
        return
    key = f"dialogue:{call_id}"
    payload = json.dumps({"step": step, "refusals": refusals, "opened": opened})
    _memory[key] = payload
    client = _client()
    if client is None:
        return
    try:
        await client.set(key, payload, ex=_TTL)
    except Exception:
        return
