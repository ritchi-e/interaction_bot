"""OpenAI-compatible TTS facade over dhee-indic-f5.

Keeps the same contract as the old rumik-bridge so Dograh (OpenAI TTS provider),
context-guard sentence prewarm, and backend greeting prewarm keep working:
  POST /v1/audio/speech  -> streaming audio/pcm @ 24 kHz
  POST /v1/audio/prewarm
  GET  /v1/models
  GET  /health
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

from engine import SAMPLE_RATE, TtsEngine

log = logging.getLogger("speech_tts")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

API_TOKEN = (os.environ.get("SPEECH_API_TOKEN") or "").strip()
PREWARM_TTL = float(os.environ.get("TTS_PREWARM_TTL", "120"))
PREWARM_MAX = int(os.environ.get("TTS_PREWARM_MAX", "64"))


def _auth_ok(request: Request) -> bool:
    if not API_TOKEN:
        return True
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip() == API_TOKEN
    if auth.lower().startswith("token "):
        return auth.split(" ", 1)[1].strip() == API_TOKEN
    return request.headers.get("x-api-key", "") == API_TOKEN


class Prewarmed:
    def __init__(self) -> None:
        self.chunks: list[bytes] = []
        self.event = asyncio.Event()
        self.done = False
        self.error: str | None = None
        self.created = time.monotonic()

    def append(self, chunk: bytes) -> None:
        self.chunks.append(chunk)
        self.event.set()
        self.event.clear()

    def finish(self, error: str | None = None) -> None:
        self.done = True
        self.error = error
        self.event.set()
        self.event.clear()


def _prewarm_key(body: dict) -> tuple[str, str]:
    text = " ".join((body.get("input") or body.get("text") or "").split())[:500]
    return body.get("model") or "", text


def _gc_prewarm(store: dict) -> None:
    now = time.monotonic()
    for key, pw in list(store.items()):
        if now - pw.created > PREWARM_TTL:
            store.pop(key, None)
    while len(store) > PREWARM_MAX:
        oldest = min(store, key=lambda k: store[k].created)
        store.pop(oldest, None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = TtsEngine()
    app.state.prewarm = {}
    log.info("speech-tts ready voices=%s", list(app.state.engine.voices))
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "sample_rate": SAMPLE_RATE,
        "voices": list(app.state.engine.voices),
    }


@app.get("/v1/models")
def models():
    data = [{"id": vid, "object": "model", "owned_by": "selfhost"} for vid in app.state.engine.voices]
    data.append({"id": "gpt-4o-mini-tts", "object": "model", "owned_by": "selfhost"})
    return {"object": "list", "data": data}


async def _fill_prewarm(engine: TtsEngine, voice: str, text: str, pw: Prewarmed) -> None:
    try:
        def run():
            return list(engine.synthesize_pcm(voice, text))

        chunks = await asyncio.to_thread(run)
        for chunk in chunks:
            pw.append(chunk)
        pw.finish()
    except Exception as exc:
        log.warning("prewarm failed: %s", exc)
        pw.finish(error=str(exc))


async def _consume_prewarmed(pw: Prewarmed):
    idx = 0
    while True:
        if idx < len(pw.chunks):
            yield pw.chunks[idx]
            idx += 1
            continue
        if pw.done:
            if pw.error and idx == 0:
                raise RuntimeError(pw.error)
            return
        await pw.event.wait()


@app.post("/v1/audio/prewarm")
async def prewarm(request: Request):
    if not _auth_ok(request):
        return Response(status_code=401)
    body = await request.json()
    model, text = _prewarm_key(body)
    if not text:
        return Response(status_code=400)
    store = request.app.state.prewarm
    _gc_prewarm(store)
    key = (model, text)
    if key not in store:
        pw = Prewarmed()
        store[key] = pw
        asyncio.create_task(_fill_prewarm(request.app.state.engine, model, text, pw))
        log.info("prewarm started (%d chars, %s)", len(text), model)
    return {"status": "ok"}


@app.post("/v1/audio/speech")
async def speech(request: Request):
    if not _auth_ok(request):
        return Response(status_code=401)
    body = await request.json()
    model, text = _prewarm_key(body)
    if not text:
        return Response(status_code=400)

    engine: TtsEngine = request.app.state.engine
    started = time.perf_counter()
    pw = request.app.state.prewarm.get((model, text))

    async def live_body():
        # Start the HTTP response immediately so Dograh's TTS client does not
        # time out while the first clause is still generating.
        yield b"\x00" * 4800

        def run():
            return list(engine.synthesize_pcm(model, text))

        try:
            chunks = await asyncio.to_thread(run)
        except Exception as exc:
            log.warning("synth failed: %s", exc)
            return
        first = True
        for chunk in chunks:
            if first:
                log.info(
                    "first audio %.0fms (%d chars, %s)",
                    (time.perf_counter() - started) * 1000,
                    len(text),
                    model,
                )
                first = False
            yield chunk

    async def cached_body():
        served = False
        try:
            async for chunk in _consume_prewarmed(pw):
                served = True
                yield chunk
        except Exception as exc:
            if served:
                log.warning("prewarm ended early: %s", exc)
                return
            log.warning("prewarm unusable, live fallback: %s", exc)
            async for chunk in live_body():
                yield chunk
            return
        if served:
            log.info("served prewarmed (%d chars)", len(text))
        else:
            async for chunk in live_body():
                yield chunk

    if pw is not None:
        return StreamingResponse(cached_body(), media_type="audio/pcm")
    return StreamingResponse(live_body(), media_type="audio/pcm")
