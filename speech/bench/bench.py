#!/usr/bin/env python3
"""Latency bench for self-hosted speech-stt / speech-tts.

Targets on a 24GB GPU (see plan):
  STT EndOfTurn <= 450ms p50 after speech ends
  TTS first audio <= 250ms p50
  TTS RTF <= 0.15

Usage:
  SPEECH_STT_URL=http://127.0.0.1:8000 SPEECH_TTS_URL=http://127.0.0.1:8001/v1 \
    python speech/bench/bench.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import struct
import time
import wave
from pathlib import Path

import httpx

try:
    import websockets
except ImportError:
    websockets = None


STT_URL = os.environ.get("SPEECH_STT_URL", "http://speech-stt:8000").rstrip("/")
TTS_URL = os.environ.get("SPEECH_TTS_URL", "http://speech-tts:8000/v1").rstrip("/")
TOKEN = os.environ.get("SPEECH_API_TOKEN", "")


def _pcm_tone(seconds: float, sr: int = 16000, freq: float = 220.0) -> bytes:
    import math

    n = int(seconds * sr)
    out = bytearray()
    for i in range(n):
        sample = int(0.2 * math.sin(2 * math.pi * freq * i / sr) * 32767)
        out.extend(struct.pack("<h", sample))
    return bytes(out)


def _pcm_silence(seconds: float, sr: int = 16000) -> bytes:
    return b"\x00\x00" * int(seconds * sr)


async def bench_stt(concurrency: int, trials: int) -> dict:
    if websockets is None:
        return {"error": "websockets not installed"}
    ws_base = STT_URL.replace("https://", "wss://").replace("http://", "ws://")
    url = f"{ws_base}/v2/listen?model=flux-general-multi&sample_rate=16000&encoding=linear16&eot_threshold=0.7&eager_eot_threshold=0.5&eot_timeout_ms=1200&language_hint=hi"
    headers = {}
    if TOKEN:
        headers["Authorization"] = f"Token {TOKEN}"

    latencies: list[float] = []

    async def one() -> None:
        speech = _pcm_tone(0.8)
        silence = _pcm_silence(0.8)
        async with websockets.connect(url, additional_headers=headers, max_size=None) as ws:
            # Connected
            await ws.recv()
            # Stream speech in 20ms frames
            frame = int(16000 * 0.02) * 2
            for i in range(0, len(speech), frame):
                await ws.send(speech[i : i + frame])
                await asyncio.sleep(0.02)
            silence_started = time.perf_counter()
            for i in range(0, len(silence), frame):
                await ws.send(silence[i : i + frame])
                await asyncio.sleep(0.02)
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.01)
                except asyncio.TimeoutError:
                    continue
                data = json.loads(msg) if isinstance(msg, str) else json.loads(msg.decode())
                if data.get("type") == "TurnInfo" and data.get("event") == "EndOfTurn":
                    latencies.append((time.perf_counter() - silence_started) * 1000)
                    return
            # Drain a bit more
            deadline = time.perf_counter() + 2.0
            while time.perf_counter() < deadline:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.05)
                except asyncio.TimeoutError:
                    continue
                data = json.loads(msg) if isinstance(msg, str) else json.loads(msg.decode())
                if data.get("type") == "TurnInfo" and data.get("event") == "EndOfTurn":
                    latencies.append((time.perf_counter() - silence_started) * 1000)
                    return

    for _ in range(trials):
        await asyncio.gather(*[one() for _ in range(concurrency)])

    if not latencies:
        return {"error": "no EndOfTurn observed", "n": 0}
    latencies.sort()
    return {
        "n": len(latencies),
        "p50_ms": statistics.median(latencies),
        "p90_ms": latencies[int(0.9 * (len(latencies) - 1))],
        "target_p50_ms": 450,
        "pass": statistics.median(latencies) <= 450,
    }


async def bench_tts(concurrency: int, trials: int) -> dict:
    texts = [
        "नमस्ते, मैं सिया बोल रही हूँ।",
        "Hello, this is Siya from customer support.",
        "आपका order confirm हो गया है, thank you.",
    ]
    first_ms: list[float] = []
    rtfs: list[float] = []
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    async def one(text: str, model: str) -> None:
        started = time.perf_counter()
        first = None
        total = 0
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{TTS_URL}/audio/speech",
                headers=headers,
                json={"input": text, "model": model},
            ) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes():
                    if not chunk:
                        continue
                    if first is None and any(b != 0 for b in chunk):
                        first = (time.perf_counter() - started) * 1000
                    total += len(chunk)
        if first is not None:
            first_ms.append(first)
        audio_s = total / (24000 * 2)
        wall = time.perf_counter() - started
        if audio_s > 0:
            rtfs.append(wall / audio_s)

    models = [
        "selfhost-hi-female",
        "selfhost-en-female",
        "selfhost-hi-male",
    ]
    for _ in range(trials):
        await asyncio.gather(
            *[one(texts[i % 3], models[i % 3]) for i in range(concurrency)]
        )

    if not first_ms:
        return {"error": "no audio", "n": 0}
    first_ms.sort()
    return {
        "n": len(first_ms),
        "first_audio_p50_ms": statistics.median(first_ms),
        "first_audio_p90_ms": first_ms[int(0.9 * (len(first_ms) - 1))],
        "rtf_p50": statistics.median(rtfs) if rtfs else None,
        "target_first_audio_p50_ms": 250,
        "target_rtf": 0.15,
        "pass": statistics.median(first_ms) <= 250 and (not rtfs or statistics.median(rtfs) <= 0.15),
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 4, 8])
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--stt-only", action="store_true")
    parser.add_argument("--tts-only", action="store_true")
    args = parser.parse_args()
    report = {"stt": {}, "tts": {}}
    for c in args.concurrency:
        if not args.tts_only:
            report["stt"][str(c)] = await bench_stt(c, args.trials)
        if not args.stt_only:
            report["tts"][str(c)] = await bench_tts(c, args.trials)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
