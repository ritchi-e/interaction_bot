"""OpenAI-compatible chat endpoint that Dograh uses as its language model.

Dograh's agent prompt only carries the campaign id. This process throws that
prompt away, loads the locked prompt from the Django API, and checks every
sentence of the model output before it is returned.
"""

import asyncio
import json
import os
import re

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from guard import (
    SAFE_FALLBACK,
    caller_is_done,
    caller_wants_more,
    closing_instruction,
    closing_line,
    without_end_call,
    extract_ids,
    force_sampling,
    guard_text,
    is_farewell,
    prepare_messages,
    split_sentences,
    take_complete,
    validate_sentence,
)

app = FastAPI(title="context-guard")

# Prewarm calls to speech-tts (see start_voice()) must never block the token
# stream back to Dograh -- that would add a full extra network round trip of
# latency to every spoken sentence, which is exactly the opposite of what
# prewarming is for. Fire them in the background and keep a strong reference
# so asyncio doesn't garbage-collect the task mid-flight.
_BACKGROUND_TASKS: set[asyncio.Task] = set()


def fire_and_forget(coro):
    task = asyncio.create_task(coro)
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)
    return task

UPSTREAM = os.environ.get("UPSTREAM_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
UPSTREAM_KEY = os.environ.get("UPSTREAM_LLM_API_KEY", "")
BACKEND = os.environ.get("BACKEND_INTERNAL_URL", "http://127.0.0.1:8000").rstrip("/")
INTERNAL_TOKEN = os.environ.get("INTERNAL_API_TOKEN", "")
MODEL_NAME = os.environ.get("UPSTREAM_LLM_MODEL", "gpt-4o-mini")
SPEECH_TTS = (
    os.environ.get("SPEECH_TTS_URL")
    or os.environ.get("RUMIK_BRIDGE_URL")
    or "http://speech-tts:8000/v1"
).rstrip("/")
SPEECH_API_TOKEN = (os.environ.get("SPEECH_API_TOKEN") or "").strip()


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


def _keep_tool_calls(calls, handoff_indexes):
    """Drop request_handoff, including the later chunks of the same call.

    Dograh has no such tool. Returning it makes Dograh run the model again,
    which is how the closing line starts looping.
    """
    kept = []
    handed_off = False
    for call in calls or []:
        name = ((call.get("function") or {}).get("name")) or ""
        index = call.get("index", 0)
        if name == "request_handoff":
            handoff_indexes.add(index)
        if index in handoff_indexes:
            handed_off = True
            continue
        kept.append(call)
    return kept, handed_off


def _without_signoff(spoken):
    """Remove a goodbye so the end-call node can say the closing line once.

    A reply that still asks a question is left alone: they are not finished.
    """
    parts = [part.strip() for part in re.split(r"(?<=[.!?।])\s+", spoken) if part.strip()]
    if not parts or any("?" in part for part in parts):
        return spoken, False
    kept = [part for part in parts if not is_farewell(part)]
    return " ".join(kept).strip(), len(kept) < len(parts)


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
    # The end node only has to say the closing line. Calling the model here is
    # what made it say that line, then say it again, without ever dropping the call.
    line = closing_line(closing) if closing else ""
    if line:
        if stream:
            async def close_once():
                yield chunk(line if line.endswith((" ", "।", ".", "?")) else line + " ")
                yield chunk(finish="stop")
                yield "data: [DONE]\n\n"

            return StreamingResponse(close_once(), media_type="text/event-stream")
        return JSONResponse(completion(line, stream=False))

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
    voice_model = policy.get("voice_model") or ""

    async def start_voice(text):
        """Optionally prewarm the first sentence — skipped for Parler.

        Parler is single-flight on the GPU. Speculative prewarm races the live
        /v1/audio/speech request and queues behind the lock, so Dograh hears
        multi-second gaps. Live streaming TTFA (~1–1.5s) is faster than a
        contended prewarm. Piper/F5 still benefit from first-sentence prewarm.
        """
        if "parler" in (voice_model or "").lower():
            return
        sentences = split_sentences(text) or []
        line = " ".join((sentences[0] or "").split()) if sentences else ""
        if not line or not voice_model:
            return
        try:
            headers = (
                {"Authorization": f"Bearer {SPEECH_API_TOKEN}"}
                if SPEECH_API_TOKEN
                else {}
            )
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.post(
                    f"{SPEECH_TTS}/audio/prewarm",
                    json={"input": line, "model": voice_model},
                    headers=headers,
                )
                if resp.status_code >= 400:
                    import logging

                    logging.getLogger("context_guard").warning(
                        "prewarm failed status=%s model=%s chars=%d",
                        resp.status_code,
                        voice_model,
                        len(line),
                    )
        except httpx.HTTPError:
            return

    async def generate():
        buffer = ""
        blocked = False
        saw_done = False
        signing_off = False
        handed_off = False
        spoke = False
        handoff_indexes = set()

        def speak(text):
            nonlocal spoke
            if not text:
                return None
            spoke = True
            return chunk(text if text.endswith(" ") else text + " ")

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
                        kept, saw_handoff = _keep_tool_calls(delta["tool_calls"], handoff_indexes)
                        handed_off = handed_off or saw_handoff
                        if any(
                            ((call.get("function") or {}).get("name")) == "done" for call in kept
                        ):
                            saw_done = True
                        if kept:
                            yield chunk(tool_calls=kept)
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
                        spoken, signed = _without_signoff(spoken)
                        signing_off = signing_off or signed
                        frame = speak(spoken)
                        if frame:
                            fire_and_forget(start_voice(spoken))
                            yield frame
                    if violations:
                        fire_and_forget(record_violations(policy, call_request_id, violations))
                    if blocked_now:
                        blocked = True
                        buffer = ""
        if buffer.strip() and not blocked and not ending:
            spoken, _rest, violations, _blocked = screen_piece(
                buffer, facts, forbidden, competitors, handoff, flush=True
            )
            fire_and_forget(record_violations(policy, call_request_id, violations))
            if spoken:
                spoken, signed = _without_signoff(spoken)
                signing_off = signing_off or signed
                frame = speak(spoken)
                if frame:
                    fire_and_forget(start_voice(spoken))
                    yield frame
        if handed_off and not spoke and not blocked and not ending and not signing_off:
            fire_and_forget(start_voice(handoff))
            yield chunk(handoff)
        if (ending or signing_off) and not saw_done:
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
