"""Thin OpenAI-compatible facade in front of Maya 2 Native.

Dograh keeps sending campaign model ids (hi_female, hi_male_hinglish, …)
and voice=alloy. Maya expects a named preset voice + language code. This
proxy remaps, strips Svara style tags, and streams PCM back unchanged.
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

MAYA_URL = os.environ.get("MAYA_UPSTREAM_URL", "http://maya-tts-api:8080").rstrip("/")
SPEECH_API_TOKEN = (os.environ.get("SPEECH_API_TOKEN") or "").strip()
DEFAULT_FEMALE = os.environ.get("MAYA_VOICE_FEMALE", "Ahana")
DEFAULT_MALE = os.environ.get("MAYA_VOICE_MALE", "Ritvik")
DEFAULT_EN_FEMALE = os.environ.get("MAYA_VOICE_EN_FEMALE", "Tanushree")
DEFAULT_EN_MALE = os.environ.get("MAYA_VOICE_EN_MALE", "Siddhant")

# Campaign model id → (Maya voice, language). Hinglish uses Hindi lang;
# Maya handles Latin loanwords better with its normaliser than a forced en tag.
_PRESETS: dict[str, tuple[str, str]] = {
    "hi_female": (DEFAULT_FEMALE, "hi"),
    "hi_male": (DEFAULT_MALE, "hi"),
    "hi_female_hinglish": (DEFAULT_FEMALE, "hi"),
    "hi_male_hinglish": (DEFAULT_MALE, "hi"),
    "en_female": (DEFAULT_EN_FEMALE, "en"),
    "en_male": (DEFAULT_EN_MALE, "en"),
}

_STYLE_TAG = re.compile(
    r"</?(?:chat|happy|sad|angry|excited|whisper|laughs?|pause|short_pause|long_pause)[^>]*>",
    re.IGNORECASE,
)

app = FastAPI(title="Maya TTS proxy", version="1.0.0")


def _authorized(authorization: str | None, x_api_key: str | None) -> bool:
    if not SPEECH_API_TOKEN:
        return True
    if x_api_key and x_api_key.strip() == SPEECH_API_TOKEN:
        return True
    if not authorization:
        return False
    scheme, _, value = authorization.partition(" ")
    token = value.strip() if value else scheme.strip()
    if scheme.lower() in {"bearer", "token"} and not value:
        token = ""
    if scheme.lower() in {"bearer", "token"}:
        return token == SPEECH_API_TOKEN
    return authorization.strip() == SPEECH_API_TOKEN


def _clean_text(text: str) -> str:
    cleaned = _STYLE_TAG.sub(" ", text or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def _resolve(body: dict[str, Any]) -> tuple[str, str, str]:
    model = str(body.get("model") or "").strip()
    voice = str(body.get("voice") or "").strip()
    language = str(body.get("language") or body.get("lang") or "").strip().lower()
    text = _clean_text(str(body.get("input") or body.get("text") or ""))
    if not text:
        raise HTTPException(status_code=400, detail="input is required")

    key = model if model in _PRESETS else (voice if voice in _PRESETS else "")
    if key:
        maya_voice, lang = _PRESETS[key]
        return text, maya_voice, language or lang

    # Pass through a real Maya voice name; default language/voice otherwise.
    if voice and voice.lower() not in {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}:
        return text, voice, language or "hi"
    return text, DEFAULT_FEMALE, language or "hi"


@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            upstream = await client.get(f"{MAYA_URL}/health")
        ready = upstream.status_code == 200
        return JSONResponse(
            {"status": "ok" if ready else "starting", "upstream": upstream.status_code},
            status_code=200 if ready else 503,
        )
    except httpx.HTTPError as exc:
        return JSONResponse({"status": "starting", "error": str(exc)}, status_code=503)


@app.get("/v1/models")
async def models(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    if not _authorized(authorization, x_api_key):
        raise HTTPException(status_code=401, detail="unauthorized")
    data = [{"id": name, "object": "model"} for name in _PRESETS]
    data.append({"id": "maya2-native", "object": "model"})
    return {"object": "list", "data": data}


@app.post("/v1/audio/prewarm")
async def prewarm(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    if not _authorized(authorization, x_api_key):
        raise HTTPException(status_code=401, detail="unauthorized")
    # Best-effort: fire one short synthesis and discard. Failures are ignored
    # by callers; we still return 204 so the greeting path stays quiet.
    try:
        body = await request.json()
    except Exception:
        body = {}
    model = str((body or {}).get("model") or "hi_female")
    text, voice, language = _resolve(
        {"input": (body or {}).get("input") or "नमस्ते।", "model": model}
    )
    payload = {
        "input": text,
        "voice": voice,
        "language": language,
        "response_format": "pcm",
        "model": "maya3",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", f"{MAYA_URL}/v1/audio/speech", json=payload) as resp:
                async for _ in resp.aiter_bytes():
                    pass
    except httpx.HTTPError:
        pass
    return Response(status_code=204)


@app.post("/v1/audio/speech")
async def speech(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    if not _authorized(authorization, x_api_key):
        raise HTTPException(status_code=401, detail="unauthorized")
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="expected json object")
    text, voice, language = _resolve(body)
    response_format = str(body.get("response_format") or "pcm").lower()
    if response_format not in {"pcm", "wav", "mp3", "opus", "flac"}:
        response_format = "pcm"

    payload = {
        "input": text,
        "voice": voice,
        "language": language,
        "response_format": response_format,
        "model": "maya3",
        "normalize": body.get("normalize", True),
    }

    client = httpx.AsyncClient(timeout=None)
    try:
        req = client.build_request("POST", f"{MAYA_URL}/v1/audio/speech", json=payload)
        upstream = await client.send(req, stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"maya upstream unreachable: {exc}") from exc

    if upstream.status_code >= 400:
        err = await upstream.aread()
        await upstream.aclose()
        await client.aclose()
        return Response(content=err, status_code=upstream.status_code, media_type="application/json")

    media = upstream.headers.get("content-type") or (
        "audio/pcm" if response_format == "pcm" else f"audio/{response_format}"
    )

    async def stream():
        try:
            async for chunk in upstream.aiter_bytes():
                if chunk:
                    yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    headers = {"X-Sample-Rate": "24000", "X-Maya-Voice": voice, "X-Maya-Language": language}
    return StreamingResponse(stream(), media_type=media, headers=headers)
