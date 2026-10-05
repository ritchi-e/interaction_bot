"""TTS engine: Piper (fast VITS) for Hindi + dhee-indic-f5 for quality/English."""

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
import torch

from cache import PcmCache
from piper_engine import PiperEngine
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
# When 1, skip loading F5 so container starts fast (Hindi Piper only).
PIPER_ONLY = os.environ.get("TTS_PIPER_ONLY", "0") == "1"


@dataclass
class Voice:
    id: str
    ref_audio: Path
    ref_text: str
    language: str
    backend: str = "f5"


class TtsEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.model = None
        self.voices: dict[str, Voice] = {}
        self.piper = PiperEngine()
        self.cache = PcmCache(
            max_items=int(os.environ.get("TTS_CACHE_ITEMS", "256")),
            disk_dir=os.environ.get("TTS_CACHE_DIR", "/models/tts/cache"),
        )
        self._load_voices()
        if not PIPER_ONLY:
            self._load_model()
        else:
            log.info("TTS_PIPER_ONLY=1 — skipping F5 load")
        self._warm_piper()

    def _load_voices(self) -> None:
        raw = json.loads(VOICES_JSON.read_text(encoding="utf-8"))
        for item in raw.get("voices", []):
            vid = item["id"]
            backend = item.get("backend", "f5")
            if backend == "piper":
                # Piper voices are registered from on-disk ONNX via PiperEngine.
                continue
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
                backend="f5",
            )

        for vid, info in self.piper.voices.items():
            self.voices[vid] = Voice(
                id=vid,
                ref_audio=Path(""),
                ref_text="",
                language=info.language,
                backend="piper",
            )

        if not self.voices:
            raise RuntimeError(f"no voices defined in {VOICES_JSON} and no piper models")
        log.info("voices: %s", list(self.voices))

    def _warm_piper(self) -> None:
        for vid in list(self.piper.voices):
            try:
                list(self.piper.synthesize_pcm(vid, "नमस्ते।"))
            except Exception as exc:
                log.warning("piper warm-up failed for %s: %s", vid, exc)

    def _load_model(self) -> None:
        import importlib.util
        import sys

        repo = str(TTS_DIR) if TTS_DIR.exists() and any(TTS_DIR.iterdir()) else os.environ.get(
            "DHEE_HF_ID", "dheeyantra/dhee-indic-f5"
        )
        log.info("loading TTS from %s on %s nfe=%d", repo, DEVICE, NFE)

        # Load IndicF5 wrapper directly — AutoModel.from_pretrained uses meta-device
        # init on recent transformers and breaks Vocos / torchaudio filterbank setup.
        model_py = Path(repo) / "model.py"
        if not model_py.exists():
            raise FileNotFoundError(f"TTS model.py missing under {repo}")
        if str(TTS_DIR) not in sys.path:
            sys.path.insert(0, str(TTS_DIR))
        spec = importlib.util.spec_from_file_location("indic_f5_model", model_py)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot import {model_py}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        config = mod.INF5Config.from_pretrained(repo)
        config.name_or_path = repo
        self.model = mod.INF5Model(config)
        if hasattr(self.model, "to"):
            self.model.to(DEVICE)
        self.model.eval()
        # Optional compile — ignore failures on older GPUs / torch builds.
        if os.environ.get("TTS_TORCH_COMPILE", "0") == "1" and DEVICE.startswith("cuda"):
            try:
                self.model = torch.compile(self.model, mode="reduce-overhead")
                log.info("torch.compile enabled")
            except Exception as exc:
                log.warning("torch.compile skipped: %s", exc)

        # Warm-up each F5 system voice once so first calls stay fast.
        for voice in self.voices.values():
            if voice.backend != "f5" or not voice.ref_audio.exists():
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
            "selfhost-hi-female-fast",
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

        if voice.backend == "piper":
            if use_cache:
                hit = self.cache.get(voice.id, clean)
                if hit is not None:
                    step = 4800
                    for i in range(0, len(hit), step):
                        yield hit[i : i + step]
                    return
            collected = bytearray()
            for chunk in self.piper.synthesize_pcm(voice.id, clean):
                collected.extend(chunk)
                yield chunk
            if use_cache and collected:
                self.cache.put(voice.id, clean, bytes(collected))
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
        if self.model is None:
            raise RuntimeError("F5 model not loaded; use a *-fast Piper voice or unset TTS_PIPER_ONLY")
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
                nfe_step=NFE,
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
