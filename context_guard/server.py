"""OpenAI-compatible chat endpoint that Dograh uses as its language model.

Dograh's agent prompt only carries the campaign id. This process throws that
prompt away, loads the locked prompt from the Django API, and checks every
sentence of the model output before it is returned.
"""

import asyncio
import json
import logging
import os
import re
import time

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

log = logging.getLogger("context_guard")

from dialogue.graph import (
    advance,
    after_greeting,
    declined_pending,
    graph_for,
    graph_report,
    next_unsaid_ask,
    redirect_line,
    replace_repeated_question,
    scripted_line,
    step_block,
    yes_should_explain,
)
from dialogue.style import apply_style, choose_tag
from dialogue.intent import classify
from dialogue.state import load_state, save_state
from spoken_numbers import expand_numbers, speakable_hindi
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
    message_text,
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
    report = graph_report()
    return {"status": "ok", "graphs": report["loaded"], "graph_errors": report["errors"]}


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


def styled(text, policy, user_text="", mode="", tone=""):
    """One Svara tag at the end of the line. The model uses it for emotion."""
    spoken = for_speech(text, policy)
    if not spoken:
        return spoken
    return apply_style(spoken, choose_tag(user_text, mode, tone, spoken))


def _offered_something_else(dialogue, step_id, assistant_text):
    """True when the caller agreed to a question this step did not ask."""
    bare = _spoken_text(assistant_text)
    if not bare or ("?" not in bare and "क्या" not in bare):
        return False
    step = dialogue.step(step_id if step_id in dialogue.steps else dialogue.start)
    for line in (step.ask, step.reask):
        line = _spoken_text(line)
        if line and line in bare:
            return False
    return True


def _spoken_text(text):
    """Drop voice tags and the space they leave in front of punctuation."""
    bare = re.sub(r"<[^>]+>", "", text or "")
    bare = re.sub(r"\s+([।!?.,])", r"\1", bare)
    return " ".join(bare.split())


def _without_new_question(text):
    """A yes already answered the question. Do not ask another one."""
    parts = [part.strip() for part in re.split(r"(?<=[.!?।])\s+", text or "") if part.strip()]
    kept = [part for part in parts if "?" not in part and not part.startswith("क्या")]
    return " ".join(kept).strip()


def for_speech(text, policy):
    """Say numbers as words before Dograh splits a sentence.

    Dograh treats the dot in १०.९९ as a full stop, so the voice says the whole
    number and then the fraction, and the decimal word is never spoken.
    """
    voice = str((policy or {}).get("voice_model") or "")
    language = "English" if voice.lower().startswith("en") else "Hindi"
    spoken = expand_numbers(text or "", language)
    if language == "Hindi":
        spoken = speakable_hindi(spoken)
    return spoken


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
                spoken = styled(line, policy, "", "close", "calm")
                yield chunk(spoken if spoken.endswith((" ", "।", ".", ">", "?")) else spoken + " ")
                yield chunk(finish="stop")
                yield "data: [DONE]\n\n"

            return StreamingResponse(close_once(), media_type="text/event-stream")
        return JSONResponse(completion(line, stream=False))

    prompt = closing or policy["prompt"]
    dialogue = None if closing else graph_for(campaign_id)
    graph_mode = ""
    last_user = ""
    last_assistant = ""
    tone = ""
    follow = ""
    if dialogue is not None:
        for message in messages or []:
            if message.get("role") == "user":
                last_user = message_text(message)
            elif message.get("role") == "assistant":
                last_assistant = message_text(message)
        current, refusals, opened = await load_state(call_request_id, dialogue.start)
        if last_user.strip():
            intent = classify(last_user, dialogue)
            if not opened:
                current, graph_mode, refusals = after_greeting(dialogue, intent, refusals)
                opened = True
            elif intent == "yes" and (
                _offered_something_else(dialogue, current, last_assistant)
                or yes_should_explain(dialogue, current)
            ):
                # They agreed to a question. Say that thing before any new question.
                # If the next scripted line is only another question, move the
                # step forward so the same offer is not explained forever.
                if yes_should_explain(dialogue, current) and not _offered_something_else(
                    dialogue, current, last_assistant
                ):
                    current, graph_mode, refusals = advance(dialogue, current, intent, refusals)
                graph_mode = "answer"
                follow = re.sub(r"<[^>]+>", "", last_assistant).strip()
            else:
                current, graph_mode, refusals = advance(dialogue, current, intent, refusals)
            await save_state(call_request_id, current, refusals, opened)
        else:
            graph_mode = "ask"
    if dialogue is not None and graph_mode in {"redirect", "ask", "reask"}:
        salt = f"{call_request_id}:{last_user}"
        if graph_mode == "redirect":
            spoken = redirect_line(dialogue, current, salt)
        else:
            spoken = scripted_line(dialogue, current, graph_mode, salt)
        tone = dialogue.step(current).tone
        spoken = styled(spoken, policy, last_user, graph_mode, tone)
        log.info(
            "dialogue campaign=%s step=%s mode=%s",
            campaign_id,
            current,
            graph_mode,
        )
        if stream:
            async def redirect_now():
                yield chunk(spoken if spoken.endswith(" ") else spoken + " ")
                yield chunk(finish="stop")
                yield "data: [DONE]\n\n"

            return StreamingResponse(redirect_now(), media_type="text/event-stream")
        return JSONResponse(completion(spoken, stream=False))
    if dialogue is not None and graph_mode != "close":
        tone = dialogue.step(current).tone
        prompt = prompt.rstrip() + "\n\n" + step_block(
            dialogue,
            current,
            graph_mode,
            follow,
            avoid_repeat=declined_pending(last_user),
        )
    repeat_used = False

    def _swap_repeated_question(text):
        """One follow-up, and not the question they just answered with no."""
        nonlocal repeat_used
        if dialogue is None or graph_mode != "answer" or not declined_pending(last_user):
            return text
        step = dialogue.step(current)
        replacement = "" if repeat_used else next_unsaid_ask(dialogue, current)
        swapped = replace_repeated_question(text, step.ask, step.reask, replacement)
        if swapped != (text or "").strip() and replacement:
            repeat_used = True
        return swapped

    def _unanswered_fallback():
        """Speak the handoff when the model only calls the handoff tool.

        A no plus a new question still gets the next unsaid question, not the
        one they already answered.
        """
        lines = [handoff]
        if dialogue is not None and declined_pending(last_user):
            nxt = next_unsaid_ask(dialogue, current)
            if nxt:
                lines.append(nxt)
        return " ".join(line for line in lines if line).strip()

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
        tools = message.get("tool_calls") or []
        handed = any((tool.get("function") or {}).get("name") == "request_handoff" for tool in tools)
        if not (message.get("content") or "").strip() and handed:
            guarded, violations = _unanswered_fallback(), []
            message.pop("tool_calls", None)
        else:
            guarded, violations = guard_text(message.get("content") or "", facts, forbidden, competitors, handoff)
            guarded = _swap_repeated_question(guarded)
        if follow:
            guarded = _without_new_question(guarded)
        guarded = styled(guarded, policy, last_user, graph_mode, tone)
        await record_violations(policy, call_request_id, violations)
        message["content"] = guarded
        payload["choices"][0]["message"] = message
        return JSONResponse(payload)

    # With a graph, only the graph decides to hang up. A first bare no is a
    # sales try, not a goodbye. Without a graph, a clear goodbye still ends.
    if dialogue is not None:
        ending = graph_mode == "close" and not closing
    else:
        ending = caller_is_done(messages) and not closing
    voice_model = policy.get("voice_model") or ""

    # Hang up immediately — do not ask the LLM (it tends to re-answer the
    # last question when STT text is messy, instead of calling done).
    if ending:
        last_user = ""
        for message in messages or []:
            if message.get("role") == "user":
                last_user = message_text(message)
        log.info("caller done -> hangup user=%r", (last_user or "")[:160])

        async def hangup_now():
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

        return StreamingResponse(hangup_now(), media_type="text/event-stream")

    async def start_voice(text):
        """Optionally prewarm the first sentence of this spoken chunk."""
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
        t0 = time.perf_counter()
        ttft_ms: float | None = None
        out_chars = 0

        def speak(text):
            nonlocal spoke, ttft_ms, out_chars
            text = _swap_repeated_question(text)
            if follow:
                text = _without_new_question(text)
            text = styled(text, policy, last_user, graph_mode, tone)
            if not text:
                return None
            spoke = True
            out_chars += len(text)
            if ttft_ms is None:
                ttft_ms = (time.perf_counter() - t0) * 1000
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
        total_ms = (time.perf_counter() - t0) * 1000
        log.info(
            "llm stream ttft=%.0fms total=%.0fms chars=%d model=%s",
            ttft_ms if ttft_ms is not None else -1,
            total_ms,
            out_chars,
            rewritten.get("model") or MODEL_NAME,
        )
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
            fallback = styled(_unanswered_fallback(), policy, last_user, graph_mode, tone)
            fire_and_forget(start_voice(fallback))
            yield chunk(fallback if fallback.endswith(" ") else fallback + " ")
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
