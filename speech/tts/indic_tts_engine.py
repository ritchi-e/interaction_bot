"""AI4Bharat Indic-TTS (FastPitch + HiFi-GAN) for low-latency Hindi telephony.

Non-autoregressive acoustic model + GAN vocoder — typically several× realtime
on a T4, so first audio is hundreds of ms rather than multi-second Parler
generation. Hindi checkpoint ships male + female speakers jointly.

Output is resampled to 24 kHz int16 PCM to match the OpenAI-compatible
speech-tts contract used by Dograh.
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

log = logging.getLogger("speech_tts.indic_tts")

MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/models"))
INDIC_TTS_DIR = Path(
    os.environ.get("INDIC_TTS_DIR", MODELS_DIR / "tts" / "indic-tts" / "hi")
)
TARGET_SR = 24000
DEVICE = os.environ.get("INDIC_TTS_DEVICE") or os.environ.get("TTS_DEVICE", "cuda")
# Slightly slower / softer defaults — FastPitch female can sound sharp on PSTN.
SPEED = float(os.environ.get("INDIC_TTS_SPEED", "1.0"))
GAIN = float(os.environ.get("INDIC_TTS_GAIN", "1.0"))
# Per-voice gain. Female FastPitch is brighter/louder; pull it down and soft-EQ.
FEMALE_GAIN = float(os.environ.get("INDIC_TTS_FEMALE_GAIN", "0.85"))
MALE_GAIN = float(os.environ.get("INDIC_TTS_MALE_GAIN", "1.05"))
# One-pole low-pass toward ~3.2 kHz at 24 kHz to tame harsh highs on female.
FEMALE_SOFTEN = os.environ.get("INDIC_TTS_FEMALE_SOFTEN", "1") == "1"
FEMALE_LP_HZ = float(os.environ.get("INDIC_TTS_FEMALE_LP_HZ", "3200"))

VOICE_MAP = {
    "selfhost-hi-female-indic": {
        "speaker": "female",
        "language": "hi",
        "gender": "female",
        "label": "Hindi · Female (Indic-TTS FastPitch)",
        "gain": FEMALE_GAIN,
    },
    "selfhost-hi-male-indic": {
        "speaker": "male",
        "language": "hi",
        "gender": "male",
        "label": "Hindi · Male (Indic-TTS FastPitch)",
        "gain": MALE_GAIN,
    },
}


@dataclass
class IndicTtsVoiceInfo:
    id: str
    speaker: str
    language: str
    gender: str
    label: str
    gain: float = 1.0


class IndicTtsEngine:
    """Lazy-load one shared FastPitch+HiFiGAN synthesizer for Hindi speakers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._synth = None
        self._sample_rate = 22050
        self._device = DEVICE
        self.voices: dict[str, IndicTtsVoiceInfo] = {}
        if os.environ.get("INDIC_TTS_DISABLED", "0") == "1":
            log.warning("INDIC_TTS_DISABLED=1 — skipping Indic-TTS voices")
            return
        self._discover()
        if self.voices:
            try:
                self._load()
                log.info(
                    "indic-tts voices ready: %s device=%s sr=%d",
                    list(self.voices),
                    self._device,
                    self._sample_rate,
                )
            except Exception as exc:
                log.warning("indic-tts unavailable (%s); voices disabled", exc)
                self.voices = {}
                self._synth = None

    def _paths(self) -> dict[str, Path]:
        root = INDIC_TTS_DIR
        # Release zip lays out hi/{fastpitch,hifigan,config.json}.
        candidates = {
            "tts_checkpoint": root / "fastpitch" / "best_model.pth",
            "tts_config": root / "config.json",
            "tts_speakers": root / "fastpitch" / "speakers.pth",
            "vocoder_checkpoint": root / "hifigan" / "best_model.pth",
            "vocoder_config": root / "hifigan" / "config.json",
        }
        # Some unpacks nest as hi/hi/...
        if not candidates["tts_checkpoint"].exists() and (root / "hi").is_dir():
            nested = root / "hi"
            candidates = {
                "tts_checkpoint": nested / "fastpitch" / "best_model.pth",
                "tts_config": nested / "config.json",
                "tts_speakers": nested / "fastpitch" / "speakers.pth",
                "vocoder_checkpoint": nested / "hifigan" / "best_model.pth",
                "vocoder_config": nested / "hifigan" / "config.json",
            }
        # Fallback: fastpitch-local config if top-level config.json missing.
        if not candidates["tts_config"].exists():
            alt = candidates["tts_checkpoint"].parent / "config.json"
            if alt.exists():
                candidates["tts_config"] = alt
        return candidates

    def _discover(self) -> None:
        paths = self._paths()
        required = ("tts_checkpoint", "tts_config", "vocoder_checkpoint", "vocoder_config")
        missing = [k for k in required if not paths[k].exists()]
        if missing:
            log.warning(
                "indic-tts weights missing under %s (%s)",
                INDIC_TTS_DIR,
                ", ".join(f"{k}={paths[k]}" for k in missing),
            )
            return
        for vid, meta in VOICE_MAP.items():
            self.voices[vid] = IndicTtsVoiceInfo(
                id=vid,
                speaker=meta["speaker"],
                language=meta["language"],
                gender=meta["gender"],
                label=meta["label"],
                gain=float(meta.get("gain", 1.0)),
            )

    def _load(self) -> None:
        import torch
        from TTS.utils.synthesizer import Synthesizer

        device = self._device
        if device.startswith("cuda") and not torch.cuda.is_available():
            device = "cpu"
            log.warning("CUDA unavailable; Indic-TTS falling back to CPU")
        self._device = device

        paths = self._paths()
        log.info(
            "loading Indic-TTS FastPitch+HiFiGAN from %s on %s",
            paths["tts_checkpoint"].parent.parent,
            device,
        )
        # Coqui TTS 0.22 uses vocoder_config= (path) and tts_speakers_file=.
        kw = dict(
            tts_checkpoint=str(paths["tts_checkpoint"]),
            tts_config_path=str(paths["tts_config"]),
            vocoder_checkpoint=str(paths["vocoder_checkpoint"]),
            vocoder_config=str(paths["vocoder_config"]),
            use_cuda=device.startswith("cuda"),
        )
        if paths["tts_speakers"].exists():
            kw["tts_speakers_file"] = str(paths["tts_speakers"])
        self._synth = Synthesizer(**kw)
        # Coqui FastPitch does `g.type(torch.LongTensor)` which always creates a
        # CPU tensor — then emb_g (on CUDA) blows up. Patch the encoder to keep
        # speaker ids on the model device.
        self._patch_fastpitch_speaker_device()
        # Prefer the vocoder / TTS config sample rate when present.
        sr = getattr(self._synth, "output_sample_rate", None) or getattr(
            getattr(self._synth, "tts_config", None), "audio", {}
        )
        if isinstance(sr, dict):
            sr = sr.get("sample_rate") or sr.get("output_sample_rate")
        if not sr and getattr(self._synth, "vocoder_config", None) is not None:
            audio = getattr(self._synth.vocoder_config, "audio", None)
            if isinstance(audio, dict):
                sr = audio.get("sample_rate")
            else:
                sr = getattr(audio, "sample_rate", None) if audio is not None else None
        self._sample_rate = int(sr or 22050)

    def _patch_fastpitch_speaker_device(self) -> None:
        """Keep speaker-id tensors on the FastPitch module device."""
        import types

        import torch

        model = getattr(self._synth, "tts_model", None)
        if model is None or not hasattr(model, "_forward_encoder"):
            return
        _orig = model._forward_encoder

        def _forward_encoder(this, x, x_mask, g=None):  # noqa: ANN001
            if hasattr(this, "emb_g") and g is not None:
                # Stay on g's / module device (Coqui's LongTensor cast forced CPU).
                g = g.to(device=this.emb_g.weight.device, dtype=torch.long)
                g = this.emb_g(g)
            if g is not None:
                g = g.unsqueeze(-1)
            x_emb = this.emb(x)
            o_en = this.encoder(torch.transpose(x_emb, 1, -1), x_mask, g)
            if g is not None:
                if hasattr(this, "proj_g"):
                    g = this.proj_g(g.view(g.shape[0], -1)).unsqueeze(-1)
                o_en = o_en + g
            return o_en, x_mask, g, x_emb

        model._forward_encoder = types.MethodType(_forward_encoder, model)
        self._forward_encoder_orig = _orig

    def _resolve_speaker(self, name: str) -> str:
        """Map our male/female labels onto whatever the checkpoint calls speakers."""
        synth = self._synth
        speakers = list(getattr(synth, "speakers", None) or [])
        if not speakers:
            # Some builds expose speaker manager instead.
            mgr = getattr(synth, "tts_model", None)
            mgr = getattr(mgr, "speaker_manager", None) if mgr is not None else None
            if mgr is not None:
                speakers = list(getattr(mgr, "speaker_names", None) or [])
                if not speakers and getattr(mgr, "name_to_id", None):
                    speakers = list(mgr.name_to_id.keys())
        if not speakers:
            return name
        lower = {s.lower(): s for s in speakers}
        if name.lower() in lower:
            return lower[name.lower()]
        # Common alternates in Indic-TTS releases.
        aliases = {
            "female": ("female", "woman", "hi_female", "hindi_female", "0"),
            "male": ("male", "man", "hi_male", "hindi_male", "1"),
        }
        for cand in aliases.get(name.lower(), ()):
            if cand in lower:
                return lower[cand]
            if cand.isdigit() and int(cand) < len(speakers):
                return speakers[int(cand)]
        # Last resort: index 0 = female, 1 = male when only two speakers.
        if len(speakers) >= 2:
            return speakers[0] if name.lower() == "female" else speakers[1]
        return speakers[0]

    def synthesize_pcm(self, voice_id: str, text: str) -> Iterator[bytes]:
        if voice_id not in self.voices:
            raise KeyError(voice_id)
        clean = " ".join((text or "").split())
        if not clean:
            return
        if self._synth is None:
            raise RuntimeError("Indic-TTS model not loaded")
        # Indic-TTS char vocab is Latin/Devanagari letters without danda; map
        # common punctuation so Coqui doesn't silently drop clause boundaries.
        clean = (
            clean.replace("।", ".")
            .replace("?", "?")
            .replace("!", "!")
            .replace("，", ",")
        )

        info = self.voices[voice_id]
        started = time.perf_counter()
        with self._lock:
            speaker = self._resolve_speaker(info.speaker)
            # Coqui Synthesizer.tts returns a list/np of float samples.
            wav = self._synth.tts(
                text=clean,
                speaker_name=speaker,
                split_sentences=True,
            )
            if isinstance(wav, (list, tuple)):
                arr = np.asarray(wav, dtype=np.float32)
            else:
                arr = np.asarray(wav, dtype=np.float32).reshape(-1)

            if SPEED and abs(SPEED - 1.0) > 1e-3 and arr.size > 1:
                # Cheap resampling-based speed change (time-stretch via rate).
                new_len = max(1, int(round(arr.size / SPEED)))
                x_old = np.linspace(0.0, 1.0, arr.size, dtype=np.float64)
                x_new = np.linspace(0.0, 1.0, new_len, dtype=np.float64)
                arr = np.interp(x_new, x_old, arr).astype(np.float32)

            if self._sample_rate != TARGET_SR and arr.size:
                duration = arr.size / float(self._sample_rate)
                n_out = max(1, int(round(duration * TARGET_SR)))
                x_old = np.linspace(0.0, 1.0, arr.size, dtype=np.float64)
                x_new = np.linspace(0.0, 1.0, n_out, dtype=np.float64)
                arr = np.interp(x_new, x_old, arr).astype(np.float32)

            voice_gain = float(info.gain) * GAIN
            if voice_gain != 1.0:
                arr = arr * voice_gain
            if info.gender == "female" and FEMALE_SOFTEN and arr.size > 8:
                arr = _soften_highs(arr, TARGET_SR, FEMALE_LP_HZ)
            arr = np.clip(arr, -1.0, 1.0)
            pcm = (arr * 32767.0).astype(np.int16).tobytes()

        elapsed_ms = (time.perf_counter() - started) * 1000
        log.info(
            "indic-tts synth total=%.0fms first=%.0fms voice=%s/%s chars=%d audio=%.2fs",
            elapsed_ms,
            elapsed_ms,
            voice_id,
            info.speaker,
            len(clean),
            len(pcm) / 2 / TARGET_SR,
        )
        # Emit in ~200ms slices so HTTP streaming can start immediately after
        # the (already complete) utterance is ready — same pattern as Piper.
        step = 9600
        for i in range(0, len(pcm), step):
            yield pcm[i : i + step]


def _soften_highs(samples: np.ndarray, sr: int, cutoff_hz: float) -> np.ndarray:
    """Gentle one-pole low-pass to reduce piercing female FastPitch highs."""
    if samples.size < 2 or cutoff_hz <= 0:
        return samples
    dt = 1.0 / float(sr)
    rc = 1.0 / (2.0 * np.pi * float(cutoff_hz))
    alpha = dt / (rc + dt)
    try:
        from scipy.signal import lfilter

        # y[n] = y[n-1] + alpha*(x[n]-y[n-1])  →  b=[alpha], a=[1, alpha-1]
        return lfilter([alpha], [1.0, alpha - 1.0], samples).astype(np.float32)
    except Exception:
        out = np.empty_like(samples, dtype=np.float32)
        prev = float(samples[0])
        out[0] = prev
        for i in range(1, samples.size):
            prev = prev + alpha * (float(samples[i]) - prev)
            out[i] = prev
        return out
