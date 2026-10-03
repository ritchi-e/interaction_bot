"""dhee-indic-f5 synthesis engine with voice caching and clause pipelining."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np

from cache import PcmCache
from text import normalize, split_clauses

log = logging.getLogger("speech_tts.engine")

MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/models"))
TTS_DIR = Path(os.environ.get("TTS_MODEL_DIR", MODELS_DIR / "tts" / "dhee-indic-f5"))
VOICES_JSON = Path(os.environ.get("TTS_VOICES_JSON", Path(__file__).parent / "voices" / "voices.json"))
VOICES_DIR = Path(os.environ.get("TTS_VOICES_DIR", MODELS_DIR / "tts" / "voices"))
SAMPLE_RATE = 24000
NFE = int(os.environ.get("TTS_NFE", "16"))
DEVICE = os.environ.get("TTS_DEVICE", "cuda")
FIRST_MAX_WORDS = int(os.environ.get("TTS_FIRST_CLAUSE_WORDS", "8"))


@dataclass
class Voice:
    id: str
    ref_audio: Path
    ref_text: str
    language: str


class TtsEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.model = None
        self.voices: dict[str, Voice] = {}
        self.cache = PcmCache(
            max_items=int(os.environ.get("TTS_CACHE_ITEMS", "256")),
            disk_dir=os.environ.get("TTS_CACHE_DIR", "/models/tts/cache"),
        )
        self._load_voices()
        self._load_model()

    def _load_voices(self) -> None:
        raw = json.loads(VOICES_JSON.read_text(encoding="utf-8"))
        for item in raw.get("voices", []):
            vid = item["id"]
            audio = Path(item["ref_audio"])
            if not audio.is_absolute():
                # Prefer models volume, then image-bundled voices/.
                for base in (VOICES_DIR, VOICES_JSON.parent):
                    candidate = base / Path(item["ref_audio"]).name
                    if candidate.exists():
                        audio = candidate
                        break
            ref_text = item.get("ref_text") or ""
            ref_text_file = item.get("ref_text_file")
            if ref_text_file:
                name = Path(ref_text_file).name
                for base in (VOICES_DIR, VOICES_JSON.parent, audio.parent):
                    tp = base / name
                    if tp.exists():
                        ref_text = tp.read_text(encoding="utf-8").strip()
                        break

            self.voices[vid] = Voice(
                id=vid,
                ref_audio=audio,
                ref_text=ref_text,
                language=item.get("language", "hi"),
            )
        if not self.voices:
            raise RuntimeError(f"no voices defined in {VOICES_JSON}")
        log.info("voices: %s", list(self.voices))

    def _load_model(self) -> None:
        import torch
        from transformers import AutoModel

        repo = str(TTS_DIR) if TTS_DIR.exists() and any(TTS_DIR.iterdir()) else os.environ.get(
            "DHEE_HF_ID", "dheeyantra/dhee-indic-f5"
        )
        log.info("loading TTS from %s on %s nfe=%d", repo, DEVICE, NFE)
        dtype = torch.float16 if DEVICE.startswith("cuda") else torch.float32
        self.model = AutoModel.from_pretrained(repo, trust_remote_code=True, torch_dtype=dtype)
        if hasattr(self.model, "to"):
            self.model.to(DEVICE)
        self.model.eval()
        # Optional compile — ignore failures on older GPUs / torch builds.
        if os.environ.get("TTS_TORCH_COMPILE", "1") == "1" and DEVICE.startswith("cuda"):
            try:
                self.model = torch.compile(self.model, mode="reduce-overhead")
                log.info("torch.compile enabled")
            except Exception as exc:
                log.warning("torch.compile skipped: %s", exc)

        # Warm-up each system voice once so first calls stay fast.
        for voice in self.voices.values():
            if not voice.ref_audio.exists():
                continue
            sample = "नमस्ते।" if voice.language.startswith("hi") else "Hello."
            try:
                list(self.synthesize_pcm(voice.id, sample, use_cache=False))
            except Exception as exc:
                log.warning("TTS warm-up failed for %s: %s", voice.id, exc)
        log.info("TTS warm-up complete")

    def resolve_voice(self, model_field: str | None) -> Voice:
        if model_field and model_field in self.voices:
            return self.voices[model_field]
        for key in (
            model_field or "",
            "selfhost-hi-female",
            "selfhost-en-female",
            next(iter(self.voices)),
        ):
            if key in self.voices:
                return self.voices[key]
        raise KeyError(model_field)

    def synthesize_pcm(
        self,
        voice_id: str,
        text: str,
        *,
        use_cache: bool = True,
    ) -> Iterator[bytes]:
        voice = self.resolve_voice(voice_id)
        clean = normalize(text, voice.language)
        if not clean:
            return
        if use_cache:
            hit = self.cache.get(voice.id, clean)
            if hit is not None:
                # Stream cache in ~100ms chunks (24kHz * 2 * 0.1 = 4800 bytes).
                step = 4800
                for i in range(0, len(hit), step):
                    yield hit[i : i + step]
                return

        clauses = split_clauses(clean, first_max_words=FIRST_MAX_WORDS)
        collected = bytearray()
        for clause in clauses:
            pcm = self._synth_clause(voice, clause)
            collected.extend(pcm)
            step = 4800
            for i in range(0, len(pcm), step):
                yield pcm[i : i + step]
        if use_cache and collected:
            self.cache.put(voice.id, clean, bytes(collected))

    def _synth_clause(self, voice: Voice, clause: str) -> bytes:
        if not voice.ref_audio.exists():
            raise FileNotFoundError(
                f"reference audio missing for {voice.id}: {voice.ref_audio}. "
                "Run speech-models fetch or place consented wavs under /models/tts/voices."
            )
        started = time.perf_counter()
        with self._lock:
            audio = self.model(
                clause,
                ref_audio_path=str(voice.ref_audio),
                ref_text=voice.ref_text,
            )
        # Accept numpy / torch / list.
        if hasattr(audio, "detach"):
            audio = audio.detach().cpu().numpy()
        arr = np.asarray(audio, dtype=np.float32).reshape(-1)
        if arr.dtype == np.int16 or arr.max() > 1.5:
            pcm = np.asarray(arr, dtype=np.int16).tobytes()
        else:
            pcm = (np.clip(arr, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
        log.info(
            "synth %.0fms voice=%s chars=%d audio=%.2fs",
            (time.perf_counter() - started) * 1000,
            voice.id,
            len(clause),
            len(pcm) / (SAMPLE_RATE * 2),
        )
        return pcm
