"""Hindi VITS voices trained on the IndicTTS speakers.

The official AI4Bharat Indic-TTS release is FastPitch + HiFi-GAN only.
These checkpoints are VITS models fine-tuned on that same Hindi male and
female IndicTTS data, loaded with transformers ``VitsModel``. Output is
resampled to 24 kHz int16 PCM for the speech-tts contract.
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

log = logging.getLogger("speech_tts.indic_vits")

MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/models"))
VITS_DIR = Path(os.environ.get("INDIC_VITS_DIR", MODELS_DIR / "tts" / "indic-vits"))
TARGET_SR = 24000
DEVICE = os.environ.get("INDIC_VITS_DEVICE") or os.environ.get("TTS_DEVICE", "cuda")
# Matches the chosen samples: expressive tone, a little faster than the stock pace.
SPEAKING_RATE = float(os.environ.get("INDIC_VITS_SPEAKING_RATE", "1.10"))
NOISE_SCALE = float(os.environ.get("INDIC_VITS_NOISE_SCALE", "0.85"))
NOISE_SCALE_DURATION = float(os.environ.get("INDIC_VITS_NOISE_SCALE_DURATION", "1.0"))
GAIN = float(os.environ.get("INDIC_VITS_GAIN", "1.1"))

# Public VITS fine-tunes of the IndicTTS Hindi speakers.
_REPOS = {
    "female": os.environ.get("INDIC_VITS_FEMALE_REPO", "onecxi/mms-hindi-female-indic"),
    "male": os.environ.get("INDIC_VITS_MALE_REPO", "onecxi/mms-hindi-male-indic"),
}
VOICE_MAP = {
    "selfhost-hi-female-vits": {
        "speaker": "female",
        "language": "hi",
        "gender": "female",
        "label": "Hindi · Female (IndicTTS VITS)",
    },
    "selfhost-hi-male-vits": {
        "speaker": "male",
        "language": "hi",
        "gender": "male",
        "label": "Hindi · Male (IndicTTS VITS)",
    },
}


@dataclass
class IndicVitsVoiceInfo:
    id: str
    speaker: str
    language: str
    gender: str
    label: str


class IndicVitsEngine:
    """One VITS model per Hindi speaker. Weights stay on disk under INDIC_VITS_DIR."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._models: dict[str, object] = {}
        self._tokenizers: dict[str, object] = {}
        self._sample_rates: dict[str, int] = {}
        self._device = DEVICE
        self.voices: dict[str, IndicVitsVoiceInfo] = {}
        if os.environ.get("INDIC_VITS_DISABLED", "0") == "1":
            log.warning("INDIC_VITS_DISABLED=1 — skipping IndicTTS VITS voices")
            return
        try:
            self._load()
        except Exception as exc:
            log.warning("indic-vits unavailable (%s); voices disabled", exc)
            self.voices = {}
            self._models = {}
            self._tokenizers = {}

    def _load(self) -> None:
        import torch
        from transformers import AutoTokenizer, VitsModel

        device = self._device
        if device.startswith("cuda") and not torch.cuda.is_available():
            device = "cpu"
            log.warning("CUDA unavailable; IndicTTS VITS falling back to CPU")
        self._device = device

        loaded = []
        for vid, meta in VOICE_MAP.items():
            speaker = meta["speaker"]
            folder = VITS_DIR / speaker
            weights = folder / "model.safetensors"
            if not weights.exists():
                log.warning(
                    "indic-vits weights missing for %s at %s (repo %s)",
                    speaker,
                    weights,
                    _REPOS[speaker],
                )
                continue
            log.info("loading IndicTTS VITS %s from %s on %s", speaker, folder, device)
            tokenizer = AutoTokenizer.from_pretrained(str(folder))
            model = VitsModel.from_pretrained(str(folder))
            model.to(device)
            model.eval()
            # transformers 4.46 reads these off the module, not forward() kwargs.
            model.speaking_rate = SPEAKING_RATE
            model.noise_scale = NOISE_SCALE
            model.noise_scale_duration = NOISE_SCALE_DURATION
            self._tokenizers[speaker] = tokenizer
            self._models[speaker] = model
            self._sample_rates[speaker] = int(getattr(model.config, "sampling_rate", 16000))
            self.voices[vid] = IndicVitsVoiceInfo(
                id=vid,
                speaker=speaker,
                language=meta["language"],
                gender=meta["gender"],
                label=meta["label"],
            )
            loaded.append(vid)
        if not loaded:
            raise FileNotFoundError(f"no IndicTTS VITS weights under {VITS_DIR}")
        log.info(
            "indic-vits voices ready: %s device=%s rate=%.2f noise=%.2f duration_noise=%.2f",
            loaded,
            device,
            SPEAKING_RATE,
            NOISE_SCALE,
            NOISE_SCALE_DURATION,
        )

    def synthesize_pcm(self, voice_id: str, text: str) -> Iterator[bytes]:
        if voice_id not in self.voices:
            raise KeyError(voice_id)
        clean = " ".join((text or "").split())
        if not clean:
            return
        info = self.voices[voice_id]
        model = self._models.get(info.speaker)
        tokenizer = self._tokenizers.get(info.speaker)
        if model is None or tokenizer is None:
            raise RuntimeError("IndicTTS VITS model not loaded")

        import torch

        started = time.perf_counter()
        with self._lock:
            inputs = tokenizer(clean, return_tensors="pt")
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            with torch.no_grad():
                waveform = model(**inputs).waveform
            arr = waveform.squeeze().detach().float().cpu().numpy().astype(np.float32)

            src_sr = self._sample_rates[info.speaker]
            if src_sr != TARGET_SR and arr.size:
                arr = _resample(arr, src_sr, TARGET_SR)
            if GAIN != 1.0:
                arr = arr * GAIN
            arr = np.clip(arr, -1.0, 1.0)
            pcm = (arr * 32767.0).astype(np.int16).tobytes()

        elapsed_ms = (time.perf_counter() - started) * 1000
        log.info(
            "indic-vits synth total=%.0fms first=%.0fms voice=%s/%s chars=%d audio=%.2fs",
            elapsed_ms,
            elapsed_ms,
            voice_id,
            info.speaker,
            len(clean),
            len(pcm) / 2 / TARGET_SR,
        )
        step = 9600
        for i in range(0, len(pcm), step):
            yield pcm[i : i + step]


def _resample(samples: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    if samples.size < 2:
        return samples
    try:
        from math import gcd

        from scipy.signal import resample_poly

        g = gcd(src_sr, dst_sr)
        return resample_poly(samples, dst_sr // g, src_sr // g).astype(np.float32)
    except Exception:
        duration = samples.size / float(src_sr)
        n_out = max(1, int(round(duration * dst_sr)))
        x_old = np.linspace(0.0, 1.0, samples.size, dtype=np.float64)
        x_new = np.linspace(0.0, 1.0, n_out, dtype=np.float64)
        return np.interp(x_new, x_old, samples).astype(np.float32)
