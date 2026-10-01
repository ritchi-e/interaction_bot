"""OpenAI-compatible chat endpoint that Dograh uses as its language model.

Dograh's agent prompt only carries the campaign id. This process throws that
prompt away, loads the locked prompt from the Django API, and checks every
sentence of the model output before it is returned.
"""

import json
import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from guard import (
    SAFE_FALLBACK,
    caller_is_done,
    caller_wants_more,
    closing_instruction,
    without_end_call,
    extract_ids,
    force_sampling,
    guard_text,
    prepare_messages,
    take_complete,
    validate_sentence,
)

app = FastAPI(title="context-guard")

UPSTREAM = os.environ.get("UPSTREAM_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
UPSTREAM_KEY = os.environ.get("UPSTREAM_LLM_API_KEY", "")
BACKEND = os.environ.get("BACKEND_INTERNAL_URL", "http://127.0.0.1:8000").rstrip("/")
INTERNAL_TOKEN = os.environ.get("INTERNAL_API_TOKEN", "")
MODEL_NAME = os.environ.get("UPSTREAM_LLM_MODEL", "gpt-4o-mini")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/models")
def models():
    return {"object": "list", "data": [{"id": MODEL_NAME, "object": "model", "owned_by": "local"}]}


async def load_policy(campaign_id):
    if not campaign_id or not INTERNAL_TOKEN:
        return None
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(
            f"{BACKEND}/internal/campaigns/{campaign_id}/context/",
            headers={"X-Internal-Token": INTERNAL_TOKEN},
        )
    if response.status_code != 200:
        return None
    return response.json()


def completion(text, stream, tool_calls=None):
    message = {"role": "assistant", "content": text}
    if tool_calls:
        message["tool_calls"] = tool_calls
    if stream:
        return None
    return {
        "id": "chatcmpl-guard",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
    }


def chunk(content="", finish=None, tool_calls=None):
    delta = {}
    if content:
        delta["content"] = content
    if tool_calls:
        delta["tool_calls"] = tool_calls
    payload = {
        "id": "chatcmpl-guard",
        "object": "chat.completion.chunk",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    return f"data: {json.dumps(payload)}\n\n"


async def record_violations(policy, call_request_id, violations):
    if not violations or not INTERNAL_TOKEN:
        return
    async with httpx.AsyncClient(timeout=5.0) as client:
        for violation in violations:
            try:
                await client.post(
                    f"{BACKEND}/internal/violations/",
                    headers={"X-Internal-Token": INTERNAL_TOKEN},
                    json={
                        "campaign_id": policy.get("campaign_id"),
                        "call_request_id": call_request_id,
                        "sentence": violation["sentence"],
                        "reason": violation["reason"],
                    },
                )
            except httpx.HTTPError:
                return


def screen_piece(piece, facts, forbidden, competitors, handoff, flush=False):
    """Validate finished sentences. Leave an unfinished tail in the buffer."""
    complete, rest = take_complete(piece)
    if flush and rest.strip():
        complete.append(rest.strip())
        rest = ""
    kept = []
    violations = []
    blocked = False
    for sentence in complete:
        ok, reason = validate_sentence(sentence, facts, forbidden, competitors)
        if ok:
            kept.append(sentence)
        else:
            violations.append({"sentence": sentence, "reason": reason})
            kept.append(handoff)
            blocked = True
            break
    return " ".join(kept), rest, violations, blocked


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages") or []
    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    campaign_id, call_request_id = extract_ids(messages)
    campaign_id = str(metadata.get("campaign_id") or body.get("campaign_id") or campaign_id)
    call_request_id = str(metadata.get("call_request_id") or body.get("call_request_id") or call_request_id)

    policy = await load_policy(campaign_id)
    stream = bool(body.get("stream"))
    if policy is None:
        text = SAFE_FALLBACK
        if stream:
            async def fallback():
                yield chunk(text)
                yield chunk(finish="stop")
                yield "data: [DONE]\n\n"

            return StreamingResponse(fallback(), media_type="text/event-stream")
        return JSONResponse(completion(text, stream=False))

    closing = closing_instruction(messages)
    prompt = closing or policy["prompt"]
    rewritten = force_sampling(body, include_handoff=not closing)
    rewritten["messages"] = prepare_messages(messages, prompt)
    rewritten["model"] = MODEL_NAME
    rewritten.pop("metadata", None)
    rewritten.pop("campaign_id", None)
    rewritten.pop("call_request_id", None)
    if caller_wants_more(messages) and not closing:
        rewritten = without_end_call(rewritten)

    headers = {"Authorization": f"Bearer {UPSTREAM_KEY}"}
    facts = policy.get("facts") or ""
    handoff = policy.get("handoff_message") or SAFE_FALLBACK
    forbidden = policy.get("forbidden_topics") or []
    competitors = policy.get("competitors") or []

    if not stream:
        async with httpx.AsyncClient(timeout=60.0) as client:
            upstream = await client.post(f"{UPSTREAM}/chat/completions", json=rewritten, headers=headers)
        if upstream.status_code >= 400:
            return JSONResponse(completion(handoff, stream=False), status_code=200)
        payload = upstream.json()
        message = ((payload.get("choices") or [{}])[0].get("message")) or {}
        guarded, violations = guard_text(message.get("content") or "", facts, forbidden, competitors, handoff)
        await record_violations(policy, call_request_id, violations)
        message["content"] = guarded
        payload["choices"][0]["message"] = message
        return JSONResponse(payload)

    ending = caller_is_done(messages) and not closing

    def mentions_done(delta):
        for call in delta.get("tool_calls") or []:
            name = ((call.get("function") or {}).get("name")) or ""
            if name == "done":
                return True
        return False

    async def generate():
        buffer = ""
        blocked = False
        saw_done = False
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{UPSTREAM}/chat/completions", json=rewritten, headers=headers
            ) as upstream:
                if upstream.status_code >= 400:
                    yield chunk(handoff, finish="stop")
                    yield "data: [DONE]\n\n"
                    return
                async for line in upstream.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = ((event.get("choices") or [{}])[0].get("delta")) or {}
                    if delta.get("tool_calls"):
                        if mentions_done(delta):
                            saw_done = True
                        yield chunk(tool_calls=delta["tool_calls"])
                    if ending or blocked:
                        continue
                    piece = delta.get("content") or ""
                    if not piece:
                        continue
                    buffer += piece
                    spoken, rest, violations, blocked_now = screen_piece(
                        buffer, facts, forbidden, competitors, handoff
                    )
                    buffer = rest
                    if spoken:
                        yield chunk(spoken if spoken.endswith(" ") else spoken + " ")
                    if violations:
                        await record_violations(policy, call_request_id, violations)
                    if blocked_now:
                        blocked = True
                        buffer = ""
        if buffer.strip() and not blocked and not ending:
            spoken, _rest, violations, _blocked = screen_piece(
                buffer, facts, forbidden, competitors, handoff, flush=True
            )
            await record_violations(policy, call_request_id, violations)
            if spoken:
                yield chunk(spoken)
        if ending and not saw_done:
            yield chunk(
                tool_calls=[
                    {
                        "index": 0,
                        "id": "call_done",
                        "type": "function",
                        "function": {"name": "done", "arguments": "{}"},
                    }
                ]
            )
        yield chunk(finish="stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
