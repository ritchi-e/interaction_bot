"""Fast Piper (VITS) Hindi TTS for low-latency telephony.

Uses official rhasspy/piper-voices Hindi models (priyamvada female, rohan male)
via the piper-tts Python package. Output is resampled to 24 kHz int16 PCM to
match the existing OpenAI-compatible speech-tts contract used by Dograh.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np

log = logging.getLogger("speech_tts.piper")

MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/models"))
PIPER_DIR = Path(os.environ.get("PIPER_MODELS_DIR", MODELS_DIR / "tts" / "piper"))
TARGET_SR = 24000
# Hindi Piper voices trained from IndicTTS can run a bit fast; 1.15 slows
# delivery slightly without sounding dragged.
LENGTH_SCALE = float(os.environ.get("PIPER_LENGTH_SCALE", "1.15"))
NOISE_SCALE = float(os.environ.get("PIPER_NOISE_SCALE", "0.667"))
NOISE_W = float(os.environ.get("PIPER_NOISE_W", "0.8"))

# Best available official Piper Hindi voices (medium quality, 22.05 kHz).
VOICE_FILES = {
    "selfhost-hi-female-fast": {
        "onnx": "hi_IN-priyamvada-medium.onnx",
        "config": "hi_IN-priyamvada-medium.onnx.json",
        "language": "hi",
        "gender": "female",
        "label": "Hindi · Female (fast)",
    },
    "selfhost-hi-male-fast": {
        "onnx": "hi_IN-rohan-medium.onnx",
        "config": "hi_IN-rohan-medium.onnx.json",
        "language": "hi",
        "gender": "male",
        "label": "Hindi · Male (fast)",
    },
}


@dataclass
class PiperVoiceInfo:
    id: str
    onnx: Path
    config: Path
    language: str
    gender: str
    label: str


class PiperEngine:
    """Lazy-loaded Piper voices; safe to construct even if models are missing."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded: dict[str, object] = {}
        self.voices: dict[str, PiperVoiceInfo] = {}
        self._discover()

    def _discover(self) -> None:
        for vid, meta in VOICE_FILES.items():
            onnx = PIPER_DIR / meta["onnx"]
            cfg = PIPER_DIR / meta["config"]
            if not onnx.exists() or not cfg.exists():
                log.warning("piper voice missing id=%s onnx=%s", vid, onnx)
                continue
            self.voices[vid] = PiperVoiceInfo(
                id=vid,
                onnx=onnx,
                config=cfg,
                language=meta["language"],
                gender=meta["gender"],
                label=meta["label"],
            )
        if self.voices:
            log.info("piper voices ready: %s", list(self.voices))
        else:
            log.warning("no piper voices found under %s", PIPER_DIR)

    def _get_voice(self, voice_id: str):
        if voice_id in self._loaded:
            return self._loaded[voice_id]
        info = self.voices[voice_id]
        from piper import PiperVoice

        # use_cuda=False: Piper VITS is already <<100ms on CPU and avoids
        # contending with the F5 diffusion model for the T4.
        voice = PiperVoice.load(str(info.onnx), config_path=str(info.config), use_cuda=False)
        self._loaded[voice_id] = voice
        return voice

    def synthesize_pcm(self, voice_id: str, text: str) -> Iterator[bytes]:
        from piper.config import SynthesisConfig

        if voice_id not in self.voices:
            raise KeyError(voice_id)
        clean = " ".join((text or "").split())
        if not clean:
            return

        started = time.perf_counter()
        with self._lock:
            voice = self._get_voice(voice_id)
            syn_cfg = SynthesisConfig(
                length_scale=LENGTH_SCALE,
                noise_scale=NOISE_SCALE,
                noise_w_scale=NOISE_W,
            )
            # Collect float/int16 chunks from piper, then resample once.
            pieces: list[np.ndarray] = []
            src_sr = int(getattr(voice.config, "sample_rate", 22050) or 22050)
            for chunk in voice.synthesize(clean, syn_cfg):
                # piper AudioChunk: audio_int16_array or audio_float_array
                arr = getattr(chunk, "audio_int16_array", None)
                if arr is not None:
                    pieces.append(np.asarray(arr, dtype=np.int16))
                    continue
                f32 = getattr(chunk, "audio_float_array", None)
                if f32 is not None:
                    pieces.append(
                        (np.clip(np.asarray(f32, dtype=np.float32), -1.0, 1.0) * 32767.0).astype(
                            np.int16
                        )
                    )
                    continue
                raw = getattr(chunk, "audio_int16_bytes", None)
                if raw:
                    pieces.append(np.frombuffer(raw, dtype=np.int16))

        if not pieces:
            return
        pcm_i16 = np.concatenate(pieces)
        if src_sr != TARGET_SR:
            pcm_i16 = _resample_i16(pcm_i16, src_sr, TARGET_SR)
        pcm = pcm_i16.tobytes()
        log.info(
            "piper synth %.0fms voice=%s chars=%d audio=%.2fs",
            (time.perf_counter() - started) * 1000,
            voice_id,
            len(clean),
            len(pcm) / 2 / TARGET_SR,
        )
        step = 4800  # ~100ms @ 24 kHz mono int16
        for i in range(0, len(pcm), step):
            yield pcm[i : i + step]


def _resample_i16(samples: np.ndarray, src: int, dst: int) -> np.ndarray:
    if src == dst or len(samples) == 0:
        return samples
    audio = samples.astype(np.float32)
    duration = len(audio) / float(src)
    n = max(1, int(duration * dst))
    x_old = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=n, endpoint=False)
    out = np.interp(x_new, x_old, audio)
    return np.clip(out, -32768, 32767).astype(np.int16)
