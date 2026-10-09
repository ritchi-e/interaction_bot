"""OpenAI speech facade in front of vLLM-Omni Voxtral TTS.

Dograh's OpenAI TTS client only sends alloy-style voices and raw PCM, and it
does not send a language. This process maps the campaign model id onto a
Voxtral preset and streams 24 kHz s16le PCM back.
"""

from __future__ import annotations

import array
import base64
import json
import logging
import os

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

log = logging.getLogger("voxtral_proxy")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

UPSTREAM = os.environ.get("VOXTRAL_UPSTREAM", "http://voxtral-tts:8091").rstrip("/")
MODEL = os.environ.get("VOXTRAL_MODEL", "mistralai/Voxtral-4B-TTS-2603")
API_TOKEN = (os.environ.get("SPEECH_API_TOKEN") or "").strip()
TIMEOUT = float(os.environ.get("VOXTRAL_TIMEOUT", "120"))


def _auth_ok(request: Request) -> bool:
    if not API_TOKEN:
        return True
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip() == API_TOKEN
    if auth.lower().startswith("token "):
        return auth.split(" ", 1)[1].strip() == API_TOKEN
    return request.headers.get("x-api-key", "") == API_TOKEN


# hi_female / hi_male are the native Hindi speakers. The cheerful preset
# speaks Hindi with an English accent, so it stays unused.
# hi_female already peaks near full scale, so the gain is only the headroom
# that remains before the soft knee.
_HINDI_FEMALE = ("hi_female", "Hindi", 1.8)
_HINDI_MALE = ("hi_male", "Hindi", 1.8)


def resolve_voice(model: str) -> tuple[str, str, float]:
    """Map a Dograh model id to a Voxtral preset, language, and playback gain."""
    key = (model or "").strip().lower()
    english = key.startswith("en") or "en_in" in key or "english" in key
    male = "male" in key and "female" not in key
    if english:
        voice = "casual_male" if male else "casual_female"
        return voice, "English", 2.6
    if male:
        return _HINDI_MALE
    return _HINDI_FEMALE


def _amplify(pcm: bytes, gain: float) -> bytes:
    """Raise level, then ease anything past the knee so peaks do not square off."""
    if gain == 1.0 or not pcm:
        return pcm
    if len(pcm) % 2:
        pcm = pcm[:-1]
    samples = array.array("h")
    samples.frombytes(pcm)
    knee = 28000.0
    out = array.array("h")
    for sample in samples:
        value = sample * gain
        if value > knee:
            value = knee + (value - knee) * 0.2
        elif value < -knee:
            value = -knee + (value + knee) * 0.2
        if value > 32767:
            value = 32767
        elif value < -32768:
            value = -32768
        out.append(int(value))
    return out.tobytes()


app = FastAPI()


@app.get("/health")
def health():
    try:
        response = httpx.get(f"{UPSTREAM}/health", timeout=3.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="voxtral not ready") from exc
    return {"service": "voxtral-proxy", "upstream": UPSTREAM}


@app.get("/v1/models")
def models():
    return {
        "data": [
            {"id": "hi_female"},
            {"id": "hi_male"},
            {"id": "en_female"},
            {"id": "en_male"},
        ]
    }


@app.post("/v1/audio/prewarm")
async def prewarm(request: Request):
    if not _auth_ok(request):
        raise HTTPException(status_code=401, detail="unauthorized")
    body = await request.json()
    text = (body.get("input") or body.get("text") or "").strip()
    if not text:
        return {"ok": True, "skipped": True}
    voice, language, gain = resolve_voice(body.get("model") or body.get("voice") or "")
    await _synthesize(text, voice, language, gain)
    return {"ok": True, "voice": voice, "language": language}


@app.post("/v1/audio/speech")
async def speech(request: Request):
    if not _auth_ok(request):
        raise HTTPException(status_code=401, detail="unauthorized")
    body = await request.json()
    text = (body.get("input") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="input is required")
    voice, language, gain = resolve_voice(body.get("model") or "")
    log.info("speech chars=%s voice=%s language=%s gain=%.2f", len(text), voice, language, gain)

    async def chunks():
        async for chunk in _stream(text, voice, language, gain):
            yield chunk

    return StreamingResponse(chunks(), media_type="audio/pcm")


async def _stream(text: str, voice: str, language: str, gain: float):
    payload = {
        "model": MODEL,
        "input": text,
        "voice": voice,
        "language": language,
        "response_format": "pcm",
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        async with client.stream(
            "POST", f"{UPSTREAM}/v1/audio/speech", json=payload
        ) as response:
            if response.status_code != 200:
                detail = (await response.aread()).decode("utf-8", "replace")[:500]
                log.error("voxtral %s %s", response.status_code, detail)
                raise HTTPException(status_code=502, detail=detail or "voxtral failed")
            content_type = (response.headers.get("content-type") or "").lower()
            if content_type.startswith("audio/"):
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield _amplify(chunk, gain)
                return
            # vLLM-Omni streams speech.audio.delta events, each carrying
            # base64 s16le PCM. Dograh plays the body as raw PCM, so the
            # JSON must be decoded before it leaves this proxy.
            pending = b""
            async for chunk in response.aiter_bytes():
                pending += chunk
                while b"\n\n" in pending:
                    block, pending = pending.split(b"\n\n", 1)
                    pcm = _pcm_from_event(block)
                    if pcm:
                        yield _amplify(pcm, gain)
            if pending.strip():
                pcm = _pcm_from_event(pending)
                if pcm:
                    yield _amplify(pcm, gain)


def _pcm_from_event(block: bytes) -> bytes:
    for line in block.splitlines():
        if not line.startswith(b"data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == b"[DONE]":
            return b""
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            log.warning("skipping undecodable speech event")
            return b""
        audio = event.get("audio")
        if not audio:
            return b""
        return base64.b64decode(audio)
    return b""


async def _synthesize(text: str, voice: str, language: str, gain: float) -> int:
    total = 0
    async for chunk in _stream(text, voice, language, gain):
        total += len(chunk)
    return total
