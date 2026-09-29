"""Rumik text-to-speech adapter for a self-hosted Dograh (pipecat) checkout.

Dograh and pipecat do not ship a Rumik provider. Sarvam, Cartesia, and
ElevenLabs are selected in Dograh's model configuration. Use this file only
when a campaign's voice provider is Rumik.

Copy it into the Dograh API image and call ``build_rumik_tts`` from the voice
branch of Dograh's service factory.

Rumik's streaming URL is not stable enough to hard-code, so the request target
comes from ``RUMIK_API_URL``. The expected contract is an HTTP POST that
streams audio bytes:

    POST {RUMIK_API_URL}
    Authorization: Bearer {api_key}
    {"text": "...", "voice": "..."}
"""

from __future__ import annotations

import os
from typing import AsyncIterator

import httpx

try:
    from pipecat.frames.frames import ErrorFrame, TTSAudioRawFrame, TTSStartedFrame, TTSStoppedFrame
    from pipecat.services.tts_service import TTSService
except ImportError:  # Running outside the Dograh image: the HTTP client still works.
    TTSService = object  # type: ignore[misc,assignment]
    TTSAudioRawFrame = TTSStartedFrame = TTSStoppedFrame = ErrorFrame = None  # type: ignore[assignment]


async def stream_speech(
    text: str,
    *,
    api_key: str,
    voice: str,
    url: str,
    chunk_size: int = 4096,
) -> AsyncIterator[bytes]:
    """Yield audio bytes as Rumik streams them back."""
    if not url:
        raise RuntimeError("RUMIK_API_URL is not set")
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/octet-stream"}
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, json={"text": text, "voice": voice}, headers=headers) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes(chunk_size):
                if chunk:
                    yield chunk


class RumikTTSService(TTSService):
    def __init__(self, *, api_key: str, voice: str, base_url: str | None = None, sample_rate: int = 24000, **kwargs):
        if TTSService is not object:
            super().__init__(sample_rate=sample_rate, **kwargs)
        self._api_key = api_key
        self._voice = voice
        self._url = base_url or os.environ.get("RUMIK_API_URL", "")
        self._sample_rate = sample_rate

    async def run_tts(self, text: str):
        if TTSStartedFrame is None:
            raise RuntimeError("pipecat is not installed; copy this file into the Dograh image")
        try:
            yield TTSStartedFrame()
            async for chunk in stream_speech(text, api_key=self._api_key, voice=self._voice, url=self._url):
                yield TTSAudioRawFrame(chunk, self._sample_rate, 1)
            yield TTSStoppedFrame()
        except Exception as exc:
            yield ErrorFrame(error=str(exc))
            yield TTSStoppedFrame()


def build_rumik_tts(*, api_key: str, voice: str, base_url: str | None = None) -> RumikTTSService:
    return RumikTTSService(api_key=api_key, voice=voice, base_url=base_url)
