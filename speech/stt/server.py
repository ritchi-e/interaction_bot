"""Deepgram Flux-compatible streaming STT for Dograh.

Dograh's DeepgramFluxSTTService connects to:
  wss://<base>/v2/listen?model=...&sample_rate=...&encoding=linear16&...

We accept that WebSocket, decode PCM with sherpa-onnx Nemotron, and emit
TurnInfo events so Dograh owns turn-taking without talking to Deepgram.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import parse_qs

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from asr import AsrEngine
from turns import Event, TurnConfig, TurnState, flux_message

log = logging.getLogger("speech_stt")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

API_TOKEN = (os.environ.get("SPEECH_API_TOKEN") or "").strip()
DECODE_TICK_MS = float(os.environ.get("STT_DECODE_TICK_MS", "40"))

# Defaults overridden by Flux query params / Configure messages.
DEFAULT_EAGER = float(os.environ.get("STT_EAGER_EOT_THRESHOLD", "0.5"))
DEFAULT_EOT = float(os.environ.get("STT_EOT_THRESHOLD", "0.7"))
DEFAULT_EOT_TIMEOUT = float(os.environ.get("STT_EOT_TIMEOUT_MS", "1200"))
DEFAULT_EOT_SILENCE = float(os.environ.get("STT_EOT_SILENCE_MS", "300"))
DEFAULT_EAGER_SILENCE = float(os.environ.get("STT_EAGER_SILENCE_MS", "200"))


class SessionRegistry:
    def __init__(self) -> None:
        self.sessions: dict[str, "ListenSession"] = {}
        self.lock = asyncio.Lock()

    async def add(self, session: "ListenSession") -> None:
        async with self.lock:
            self.sessions[session.id] = session

    async def remove(self, session_id: str) -> None:
        async with self.lock:
            self.sessions.pop(session_id, None)

    async def active(self) -> list["ListenSession"]:
        async with self.lock:
            return list(self.sessions.values())


class ListenSession:
    def __init__(
        self,
        ws: WebSocket,
        engine: AsrEngine,
        sample_rate: int,
        language_hint: str,
        turn_config: TurnConfig,
    ) -> None:
        self.id = uuid.uuid4().hex
        self.ws = ws
        self.engine = engine
        self.sample_rate = sample_rate
        self.language = language_hint
        self.turn = TurnState(config=turn_config)
        if language_hint.startswith("en"):
            self.turn.languages = ["en"]
        else:
            self.turn.languages = ["hi"]
        self.handle = engine.create_stream(language_hint)
        self.audio_q: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=64)
        self.closed = False
        self._pcm_window = bytearray()
        self._window_max = int(sample_rate * 2 * 8)  # ~8s int16 mono

    async def send_json(self, payload: dict[str, Any]) -> None:
        if self.closed:
            return
        await self.ws.send_json(payload)

    async def push_pcm(self, pcm: bytes) -> None:
        if self.closed:
            return
        try:
            self.audio_q.put_nowait(pcm)
        except asyncio.QueueFull:
            try:
                self.audio_q.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self.audio_q.put_nowait(pcm)

    async def close(self) -> None:
        self.closed = True
        try:
            self.audio_q.put_nowait(None)
        except asyncio.QueueFull:
            pass


def _auth_ok(headers) -> bool:
    if not API_TOKEN:
        return True
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    if auth.lower().startswith("token "):
        return auth.split(" ", 1)[1].strip() == API_TOKEN
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip() == API_TOKEN
    return False


def _parse_listen_query(query_string: bytes) -> tuple[int, str, TurnConfig]:
    qs = parse_qs(query_string.decode("utf-8", errors="ignore"))

    def first(name: str, default: str = "") -> str:
        vals = qs.get(name) or []
        return vals[0] if vals else default

    sample_rate = int(first("sample_rate", "16000") or "16000")
    hints = qs.get("language_hint") or []
    language = (hints[0] if hints else first("language", "hi")).lower() or "hi"

    cfg = TurnConfig(
        eager_eot_threshold=float(first("eager_eot_threshold", str(DEFAULT_EAGER))),
        eot_threshold=float(first("eot_threshold", str(DEFAULT_EOT))),
        eot_timeout_ms=float(first("eot_timeout_ms", str(DEFAULT_EOT_TIMEOUT))),
        eot_silence_ms=DEFAULT_EOT_SILENCE,
        eager_silence_ms=DEFAULT_EAGER_SILENCE,
    )
    return sample_rate, language, cfg


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = AsrEngine()
    app.state.registry = SessionRegistry()
    app.state.decode_task = asyncio.create_task(_decode_loop(app))
    log.info("speech-stt ready")
    yield
    app.state.decode_task.cancel()
    try:
        await app.state.decode_task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    registry: SessionRegistry = app.state.registry
    return {
        "status": "ok",
        "active_sessions": len(await registry.active()),
        "provider": os.environ.get("SHERPA_PROVIDER", "cuda"),
    }


@app.websocket("/v2/listen")
async def listen(websocket: WebSocket):
    if not _auth_ok(websocket.headers):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    sample_rate, language, turn_cfg = _parse_listen_query(websocket.scope.get("query_string", b""))
    engine: AsrEngine = app.state.engine
    registry: SessionRegistry = app.state.registry
    session = ListenSession(websocket, engine, sample_rate, language, turn_cfg)
    await registry.add(session)
    await session.send_json({"type": "Connected", "request_id": session.id})
    log.info("listen open id=%s sr=%d lang=%s", session.id, sample_rate, language)

    reader = asyncio.create_task(_read_client(session))
    try:
        await reader
    finally:
        await session.close()
        await registry.remove(session.id)
        log.info("listen close id=%s", session.id)


async def _read_client(session: ListenSession) -> None:
    try:
        while True:
            message = await session.ws.receive()
            if message.get("type") == "websocket.disconnect":
                break
            if "bytes" in message and message["bytes"] is not None:
                await session.push_pcm(message["bytes"])
                continue
            text = message.get("text")
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            msg_type = data.get("type")
            if msg_type == "CloseStream":
                break
            if msg_type == "Configure":
                _apply_configure(session, data)
                await session.send_json({"type": "ConfigureSuccess"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        log.warning("client read error id=%s: %s", session.id, exc)


def _apply_configure(session: ListenSession, data: dict[str, Any]) -> None:
    cfg = session.turn.config
    if "eot_threshold" in data and data["eot_threshold"] is not None:
        cfg.eot_threshold = float(data["eot_threshold"])
    if "eager_eot_threshold" in data and data["eager_eot_threshold"] is not None:
        cfg.eager_eot_threshold = float(data["eager_eot_threshold"])
    if "eot_timeout_ms" in data and data["eot_timeout_ms"] is not None:
        cfg.eot_timeout_ms = float(data["eot_timeout_ms"])
    hints = data.get("language_hints") or data.get("language_hint")
    if hints:
        if isinstance(hints, list) and hints:
            session.language = str(hints[0]).lower()
        elif isinstance(hints, str):
            session.language = hints.lower()
        session.turn.languages = ["en"] if session.language.startswith("en") else ["hi"]


async def _decode_loop(app: FastAPI) -> None:
    engine: AsrEngine = app.state.engine
    registry: SessionRegistry = app.state.registry
    tick = DECODE_TICK_MS / 1000.0
    while True:
        started = time.perf_counter()
        sessions = await registry.active()
        for session in sessions:
            try:
                await _drain_session(engine, session)
            except Exception as exc:
                log.warning("decode error id=%s: %s", session.id, exc)
        elapsed = time.perf_counter() - started
        await asyncio.sleep(max(0.0, tick - elapsed))


async def _drain_session(engine: AsrEngine, session: ListenSession) -> None:
    chunks: list[bytes] = []
    while True:
        try:
            item = session.audio_q.get_nowait()
        except asyncio.QueueEmpty:
            break
        if item is None:
            return
        chunks.append(item)
    if not chunks:
        return

    pcm = b"".join(chunks)
    session._pcm_window.extend(pcm)
    if len(session._pcm_window) > session._window_max:
        session._pcm_window = session._pcm_window[-session._window_max :]

    # Approximate duration of this batch at the call's sample rate.
    dt_ms = (len(pcm) / 2) / max(session.sample_rate, 1) * 1000.0
    is_speech = await asyncio.to_thread(engine.is_speech, pcm, session.sample_rate)
    await asyncio.to_thread(engine.accept_pcm16, session.handle, pcm, session.sample_rate)
    texts = await asyncio.to_thread(engine.decode_batch, [session.handle])
    transcript = texts[0] if texts else session.turn.transcript

    eot_prob = None
    if not is_speech and session.turn.in_turn:
        eot_prob = await asyncio.to_thread(
            engine.end_of_turn_prob, bytes(session._pcm_window), session.sample_rate
        )

    events = session.turn.on_audio(
        is_speech=is_speech,
        dt_ms=dt_ms,
        transcript=transcript,
        eot_prob=eot_prob,
    )
    for event, payload in events:
        await session.send_json(flux_message(event, payload))


@app.get("/")
async def root():
    return JSONResponse({"service": "speech-stt", "protocol": "deepgram-flux"})
