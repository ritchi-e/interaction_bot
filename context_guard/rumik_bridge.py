"""Speak Dograh's OpenAI TTS requests with Rumik's streaming voice.

Dograh v1.47 has no Rumik provider. Point its OpenAI TTS base URL here. Dograh
asks for raw 24 kHz PCM and plays chunks as they arrive, which is exactly what
Rumik's WebSocket sends, so audio is passed through untouched.

Dograh's OpenAI TTS client only allows fixed OpenAI voice names (alloy, echo,
...), so a workflow cannot request a Rumik voice through `voice`. It can send
any string through `model`, though, since that field is passed straight
through with no allow-list. Each Dograh workflow (the local viva tester's
English/Hindi agents, and every business's published campaign workflow) sets
a different `model` string in its TTS override; PRESETS below maps each one
to the Rumik speaker + description that fits that language. The speaker and
description travel in the per-message payload on an already-open socket, so
one warm pool of connections serves every preset — no need to reconnect or
run a separate bridge per language or per business.

This one process is deployed twice: as a local terminal command for the viva
tester (see viva/setup_dograh_viva.py), and as the `rumik-bridge` service
in deploy/docker-compose.yml for the production calling system (see
backend/apps/agents/model_overrides.py for how a campaign picks a preset).
"""

import asyncio
import io
import json
import logging
import os
import ssl
import time
import wave
from contextlib import asynccontextmanager

import certifi
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse
from websockets.asyncio.client import connect

GATEWAY = os.environ.get("RUMIK_GATEWAY_URL", "https://silk-api.rumik.ai").rstrip("/")
MODEL = os.environ.get("RUMIK_TTS_MODEL", "mulberry")
WARM = int(os.environ.get("RUMIK_WS_WARM", "2"))
MAX_IDLE = int(os.environ.get("RUMIK_WS_MAX_IDLE", "8"))
FIRST_AUDIO_TIMEOUT = float(os.environ.get("RUMIK_FIRST_AUDIO_TIMEOUT", "4"))
CHUNK_TIMEOUT = float(os.environ.get("RUMIK_CHUNK_TIMEOUT", "10"))

# Keyed by the `model` string a Dograh workflow's TTS override sends. Falls
# back to DEFAULT_PRESET for a bare "gpt-4o-mini-tts" request (no override set)
# or for any unrecognized name, so old workflows keep working unchanged.
DEFAULT_PRESET = {
    "speaker": os.environ.get("RUMIK_TTS_DEFAULT_SPEAKER", "siya"),
    "description": os.environ.get(
        "RUMIK_TTS_DESCRIPTION",
        "a warm Indian woman, clear Hindi and English, short pauses, calm voice",
    ),
}
PRESETS = {
    "rumik-siya-hindi": {
        "speaker": "siya",
        "description": (
            "a warm Indian woman speaking Hindi, clear Hindi accent, natural Hindi "
            "prosody, short pauses, calm feminine voice"
        ),
    },
    "rumik-siya-english-indian": {
        "speaker": "siya",
        "description": (
            "a warm Indian woman speaking Indian English, clear Indian English "
            "accent, short pauses, calm voice"
        ),
    },
    "rumik-siya-hinglish": {
        "speaker": "siya",
        "description": (
            "a warm Indian woman speaking Hinglish, moving naturally between Hindi "
            "and English words within the same sentence, clear Indian accent, "
            "short pauses, calm voice"
        ),
    },
}


def _preset(model_field: str | None) -> dict:
    return PRESETS.get(model_field or "", DEFAULT_PRESET)

log = logging.getLogger("rumik_bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
SSL = ssl.create_default_context(cafile=certifi.where())


def _headers():
    return {"Authorization": f"Bearer {os.environ['RUMIK_API_KEY']}"}


def _payload(text, preset):
    return {"text": text, "speaker": preset["speaker"], "description": preset["description"]}


class Socket:
    """One warm Rumik connection; a reader task feeds every frame into a queue."""

    def __init__(self, ws):
        self.ws = ws
        self.queue = asyncio.Queue()
        self.alive = True
        self.reader = asyncio.create_task(self._read())

    async def _read(self):
        try:
            async for message in self.ws:
                if isinstance(message, bytes):
                    self.queue.put_nowait(message)
                    continue
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue
                if data.get("type") in ("timeout", "error") or data.get("error"):
                    self.alive = False
                self.queue.put_nowait(data)
        except Exception:
            pass
        finally:
            self.alive = False
            self.queue.put_nowait(None)

    async def next(self, timeout):
        return await asyncio.wait_for(self.queue.get(), timeout)

    async def close(self):
        self.alive = False
        self.reader.cancel()
        try:
            await self.ws.close()
        except Exception:
            pass


class Pool:
    def __init__(self, client):
        self.client = client
        self.idle = []
        self.filling = None

    async def open(self):
        minted = await self.client.post(
            f"{GATEWAY}/v1/tts/ws-connect",
            headers=_headers(),
            json={"text": "init", "model": MODEL},
            timeout=10.0,
        )
        minted.raise_for_status()
        session = minted.json()
        sep = "&" if "?" in session["ws_url"] else "?"
        url = f"{session['ws_url']}{sep}{httpx.QueryParams({'token': session['token']})}"
        ws = await connect(
            url,
            ssl=SSL if url.startswith("wss://") else None,
            ping_interval=20,
            ping_timeout=30,
            max_size=None,
            compression=None,
        )
        return Socket(ws)

    async def get(self):
        while self.idle:
            sock = self.idle.pop()
            if sock.alive:
                while not sock.queue.empty():
                    sock.queue.get_nowait()
                self.refill()
                return sock
            await sock.close()
        self.refill()
        return await self.open()

    async def put(self, sock):
        if sock.alive and len(self.idle) < MAX_IDLE:
            self.idle.append(sock)
        else:
            await sock.close()

    async def cancel_then_put(self, sock):
        try:
            await sock.ws.send(json.dumps({"type": "cancel"}))
            while True:
                item = await sock.next(3.0)
                if item is None:
                    break
                if isinstance(item, dict) and item.get("type") in ("cancelled", "done"):
                    await self.put(sock)
                    return
        except Exception:
            pass
        await sock.close()

    def refill(self):
        if self.filling is None or self.filling.done():
            self.filling = asyncio.create_task(self._fill())

    async def _fill(self):
        self.idle = [s for s in self.idle if s.alive]
        while len(self.idle) < WARM:
            try:
                self.idle.append(await self.open())
            except Exception as exc:
                log.warning("rumik warm socket failed: %s", exc)
                return

    async def close(self):
        for sock in self.idle:
            await sock.close()
        self.idle = []


@asynccontextmanager
async def lifespan(app):
    app.state.client = httpx.AsyncClient(http2=False, timeout=40.0)
    app.state.pool = Pool(app.state.client)
    await app.state.pool._fill()
    log.info(
        "rumik bridge ready, %d warm sockets, model=%s, presets=%s, default=%s",
        len(app.state.pool.idle),
        MODEL,
        list(PRESETS),
        DEFAULT_PRESET,
    )
    yield
    await app.state.pool.close()
    await app.state.client.aclose()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "warm": len(app.state.pool.idle)}


@app.get("/v1/models")
def models():
    return {"object": "list", "data": [{"id": "gpt-4o-mini-tts", "object": "model", "owned_by": "rumik"}]}


async def _start_stream(pool, text, preset):
    """Send text on a warm socket and wait for the first audio chunk."""
    sock = await pool.get()
    try:
        await sock.ws.send(json.dumps(_payload(text, preset)))
        while True:
            item = await sock.next(FIRST_AUDIO_TIMEOUT)
            if isinstance(item, bytes):
                return sock, item
            if item is None or item.get("type") in ("done", "error", "timeout", "cancelled") or item.get("error"):
                raise RuntimeError(f"rumik stream ended early: {item}")
    except BaseException:
        await sock.close()
        raise


async def _stream(pool, sock, first, started, text):
    finished = False
    total = len(first)
    try:
        yield first
        while True:
            item = await sock.next(CHUNK_TIMEOUT)
            if isinstance(item, bytes):
                total += len(item)
                yield item
                continue
            if item is None:
                break
            if item.get("type") == "done":
                finished = True
                break
            if item.get("type") in ("error", "timeout", "cancelled") or item.get("error"):
                log.warning("rumik stream stopped: %s", item)
                break
    finally:
        seconds = total / 48000
        log.info("rumik done %.0fms, %.1fs audio, %d chars%s", (time.perf_counter() - started) * 1000, seconds, len(text), "" if finished else " (cut)")
        if finished:
            await pool.put(sock)
        elif sock.alive:
            asyncio.create_task(pool.cancel_then_put(sock))
        else:
            await sock.close()


async def _http_fallback(client, text, preset):
    response = await client.post(
        f"{GATEWAY}/v1/tts",
        headers=_headers(),
        json={"model": MODEL, **_payload(text, preset)},
    )
    response.raise_for_status()
    with wave.open(io.BytesIO(response.content), "rb") as wav:
        return wav.readframes(wav.getnframes())


@app.post("/v1/audio/speech")
async def speech(request: Request):
    body = await request.json()
    text = " ".join((body.get("input") or body.get("text") or "").split())[:500]
    if not text:
        return Response(status_code=400)
    preset = _preset(body.get("model"))

    pool = request.app.state.pool
    started = time.perf_counter()

    async def body():
        # Start the response at once. Waiting here for Rumik's first sound made
        # the call close the greeting before any audio arrived.
        yield b"\x00" * 4800
        last_error = None
        for attempt in range(2):
            try:
                sock, first = await _start_stream(pool, text, preset)
                log.info(
                    "rumik first audio %.0fms (%d chars, %s)",
                    (time.perf_counter() - started) * 1000,
                    len(text),
                    preset["speaker"],
                )
                async for chunk in _stream(pool, sock, first, started, text):
                    yield chunk
                return
            except Exception as exc:
                last_error = exc
                log.warning("rumik stream attempt %d failed: %s", attempt + 1, exc)
        pcm = await _http_fallback(request.app.state.client, text, preset)
        log.info("rumik http fallback %.0fms (%d chars)", (time.perf_counter() - started) * 1000, len(text))
        if last_error:
            log.warning("served the voice from the http fallback after %s", last_error)
        yield pcm

    return StreamingResponse(body(), media_type="audio/pcm")
