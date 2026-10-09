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

from spoken_numbers import SENTENCE_GAP, SAMPLE_RATE, expand_numbers, split_sentences

# hi_male already keeps a little trailing quiet. A full 400 ms gap on top of
# that lands longer than the female voice, so the male pause is shorter.
_MALE_SENTENCE_GAP = b"\x00" * int(SAMPLE_RATE * 0.2) * 2

log = logging.getLogger("voxtral_proxy")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

UPSTREAM = os.environ.get("VOXTRAL_UPSTREAM", "http://voxtral-tts:8091").rstrip("/")
MODEL = os.environ.get("VOXTRAL_MODEL", "mistralai/Voxtral-4B-TTS-2603")
API_TOKEN = (os.environ.get("SPEECH_API_TOKEN") or "").strip()
TIMEOUT = float(os.environ.get("VOXTRAL_TIMEOUT", "120"))
# Quiet between the last word of one sentence and the first word of the next.


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
# hi_male speaks much slower and leaves a gap after almost every word.
# A higher speed plus a silence cap brings it in line with hi_female.
_HINDI_FEMALE = ("hi_female", "Hindi", 1.8, 1.0)
_HINDI_MALE = ("hi_male", "Hindi", 1.8, 1.45)


def resolve_voice(model: str) -> tuple[str, str, float, float]:
    """Map a Dograh model id to a preset, language, gain, and speaking speed."""
    key = (model or "").strip().lower()
    english = key.startswith("en") or "en_in" in key or "english" in key
    male = "male" in key and "female" not in key
    if english:
        voice = "casual_male" if male else "casual_female"
        return voice, "English", 2.6, 1.0
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
    voice, language, gain, speed = resolve_voice(body.get("model") or body.get("voice") or "")
    text = expand_numbers(text, language)
    await _synthesize(text, voice, language, gain, speed)
    return {"ok": True, "voice": voice, "language": language}


@app.post("/v1/audio/speech")
async def speech(request: Request):
    if not _auth_ok(request):
        raise HTTPException(status_code=401, detail="unauthorized")
    body = await request.json()
    text = (body.get("input") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="input is required")
    voice, language, gain, speed = resolve_voice(body.get("model") or "")
    text = expand_numbers(text, language)
    log.info(
        "speech chars=%s voice=%s language=%s gain=%.2f speed=%.2f",
        len(text),
        voice,
        language,
        gain,
        speed,
    )

    async def chunks():
        gap = _MALE_SENTENCE_GAP if voice == "hi_male" else SENTENCE_GAP
        sentences = split_sentences(text)
        for index, sentence in enumerate(sentences):
            if index:
                yield gap
            pace = _SilenceCap() if voice == "hi_male" else None
            goodbye = "अलविदा" in sentence or "alvida" in sentence.casefold()
            spoken = b""
            async for chunk in _stream(sentence, voice, language, gain, speed):
                piece = pace.push(chunk) if pace is not None else chunk
                if goodbye:
                    spoken += piece
                elif piece:
                    yield piece
            if pace is not None:
                tail = pace.flush()
                if goodbye:
                    spoken += tail
                elif tail:
                    yield tail
            if goodbye and spoken:
                yield _falling_goodbye(spoken)
        # Also after the last sentence, so the next spoken clip does not
        # start on the final word when Dograh sends one sentence per request.
        yield gap

    return StreamingResponse(chunks(), media_type="audio/pcm")


class _SilenceCap:
    """Drop the long dead air hi_male leaves between words. Keep the words."""

    def __init__(self, max_ms: int = 140, sample_rate: int = 24000):
        self._frame = int(sample_rate * 0.01) * 2  # 10 ms, s16le
        self._max_bytes = int(sample_rate * max_ms / 1000) * 2
        self._held = b""
        self._silent = 0

    def push(self, pcm: bytes) -> bytes:
        if not pcm:
            return b""
        data = self._held + pcm
        usable = len(data) - (len(data) % self._frame)
        self._held = data[usable:]
        return self._emit(data[:usable])

    def flush(self) -> bytes:
        rest = self._held
        self._held = b""
        if not rest or _quiet(rest):
            return b""
        return self._emit(rest)

    def _emit(self, data: bytes) -> bytes:
        out = bytearray()
        step = self._frame
        for start in range(0, len(data), step):
            piece = data[start : start + step]
            if _quiet(piece):
                room = self._max_bytes - self._silent
                if room <= 0:
                    continue
                piece = piece[:room]
                self._silent += len(piece)
            else:
                self._silent = 0
            out += piece
        return bytes(out)


def _falling_goodbye(pcm: bytes, sample_rate: int = 24000) -> bytes:
    """Pull the last syllable of अलविदा down.

    The voice otherwise flicks up at the end, which sounds like a question
    rather than goodbye. Slowing that tail lowers the pitch so it settles.
    """
    if len(pcm) < 4:
        return pcm
    samples = array.array("h")
    samples.frombytes(pcm[: len(pcm) // 2 * 2])
    count = len(samples)
    tail = int(sample_rate * 0.40)
    start = max(0, count - tail)
    out = array.array("h", samples[:start])
    span = count - start
    if span < 2:
        return pcm
    position = 0.0
    while position < span - 1:
        progress = position / span
        rate = 1.0 + (0.48 - 1.0) * (progress ** 1.4)
        index = start + int(position)
        fraction = position - int(position)
        first = samples[index]
        second = samples[min(index + 1, count - 1)]
        sample = first + (second - first) * fraction
        gain = 1.0 - 0.2 * (progress ** 2)
        out.append(int(sample * gain))
        position += max(rate, 0.4)
    return out.tobytes()


def _quiet(pcm: bytes, threshold: int = 80) -> bool:
    if len(pcm) < 2:
        return True
    samples = array.array("h")
    samples.frombytes(pcm[: len(pcm) // 2 * 2])
    if not samples:
        return True
    energy = sum(sample * sample for sample in samples) / len(samples)
    return energy < threshold * threshold


async def _stream(text: str, voice: str, language: str, gain: float, speed: float = 1.0):
    # Voxtral rejects speed on a streaming request. The male voice needs the
    # higher speed, so that one voice is generated whole, then paced below.
    streaming = speed == 1.0
    payload = {
        "model": MODEL,
        "input": text,
        "voice": voice,
        "language": language,
        "response_format": "pcm",
        "stream": streaming,
    }
    if not streaming:
        payload["speed"] = speed
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        if not streaming:
            response = await client.post(f"{UPSTREAM}/v1/audio/speech", json=payload)
            if response.status_code != 200:
                detail = response.text[:500]
                log.error("voxtral %s %s", response.status_code, detail)
                raise HTTPException(status_code=502, detail=detail or "voxtral failed")
            body = response.content
            if body:
                yield _amplify(body, gain)
            return
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


async def _synthesize(text: str, voice: str, language: str, gain: float, speed: float = 1.0) -> int:
    total = 0
    async for chunk in _stream(text, voice, language, gain, speed):
        total += len(chunk)
    return total
