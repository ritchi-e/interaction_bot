"""Indic Parler-TTS (AI4Bharat) with chunk streaming for low time-to-first-audio.

Uses ``ai4bharat/indic-parler-tts`` + ``ParlerTTSStreamer`` so Dograh can start
playing audio before the full utterance is decoded. Native sample rate is
typically 44.1 kHz; we resample to 24 kHz int16 PCM for the existing contract.

Hindi recommended speakers: Divya (female), Rohit (male).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Iterator

import numpy as np

log = logging.getLogger("speech_tts.parler")

TARGET_SR = 24000
DEVICE = os.environ.get("PARLER_DEVICE") or os.environ.get("TTS_DEVICE", "cuda")
# Prefer a local checkout (ModelScope/HF fetch into /models). Hub id needs
# HF_TOKEN after accepting the gated contact-info form on Hugging Face.
REPO_ID = os.environ.get("PARLER_REPO_ID", "/models/tts/indic-parler-tts")
HF_TOKEN = (
    os.environ.get("HF_TOKEN")
    or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    or None
)
# Seconds of audio per internal decode step (doesn't affect call playback pacing).
PLAY_STEPS_S = float(os.environ.get("PARLER_PLAY_STEPS_S", "0.5"))
# Soft crossfade between streamed chunks after resample (ms).
CHUNK_XFADE_MS = float(os.environ.get("PARLER_CHUNK_XFADE_MS", "12"))
# Global gain multiplier (applied after per-voice gain).
GAIN = float(os.environ.get("PARLER_GAIN", "1.0"))
# Parler on T4 is ~0.5× realtime. Streaming chunks to the phone as they generate
# causes word…gap…word underruns. Default: buffer the full utterance, then emit
# continuously. Set PARLER_STREAM_PLAYBACK=1 to restore chunky low-TTFA streaming.
STREAM_PLAYBACK = os.environ.get("PARLER_STREAM_PLAYBACK", "0") == "1"
# If >0 and STREAM_PLAYBACK is off, start emitting once this many seconds of
# audio are buffered (still generates the rest). 0 = wait for full utterance.
JITTER_BUFFER_S = float(os.environ.get("PARLER_JITTER_BUFFER_S", "0"))

VOICE_MAP = {
    "selfhost-hi-female-parler": {
        "speaker": "Divya",
        "description": (
            "Divya speaks at a natural conversational pace with a warm, slightly "
            "expressive tone and clear pronunciation. The recording is of very high "
            "quality, with the speaker's voice sounding clear, loud, and very close up."
        ),
        "language": "hi",
        "gender": "female",
        # Divya native levels are ~5× quieter than Rohit; lift toward telephony loudness.
        "gain": float(os.environ.get("PARLER_FEMALE_GAIN", "3.2")),
        "label": "Hindi · Female (Indic Parler)",
    },
    "selfhost-hi-male-parler": {
        "speaker": "Rohit",
        "description": (
            "Rohit speaks at a natural conversational pace with a clear, slightly "
            "expressive tone. The recording is of very high quality, with the "
            "speaker's voice sounding clear and very close up."
        ),
        "language": "hi",
        "gender": "male",
        "gain": float(os.environ.get("PARLER_MALE_GAIN", "1.15")),
        "label": "Hindi · Male (Indic Parler)",
    },
}


@dataclass
class ParlerVoiceInfo:
    id: str
    speaker: str
    description: str
    language: str
    gender: str
    label: str
    gain: float = 1.0


class ParlerEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model = None
        self._prompt_tok = None
        self._desc_tok = None
        self._sample_rate = 44100
        self._device = DEVICE
        self.voices: dict[str, ParlerVoiceInfo] = {
            vid: ParlerVoiceInfo(
                id=vid,
                speaker=meta["speaker"],
                description=meta["description"],
                language=meta["language"],
                gender=meta["gender"],
                label=meta["label"],
                gain=float(meta.get("gain", 1.0)),
            )
            for vid, meta in VOICE_MAP.items()
        }
        if os.environ.get("PARLER_DISABLED", "0") == "1":
            log.warning("PARLER_DISABLED=1 — skipping Indic Parler voices")
            self.voices = {}
            return
        try:
            self._load()
            log.info(
                "parler voices ready: %s device=%s sr=%d",
                list(self.voices),
                self._device,
                self._sample_rate,
            )
        except Exception as exc:
            log.warning("indic parler unavailable (%s); voices disabled", exc)
            self.voices = {}
            self._model = None

    def _load(self) -> None:
        import torch
        from parler_tts import ParlerTTSForConditionalGeneration
        from transformers import AutoTokenizer

        device = self._device
        if device.startswith("cuda") and not torch.cuda.is_available():
            device = "cpu"
            log.warning("CUDA unavailable; Indic Parler falling back to CPU")
        self._device = device
        # NOTE: deliberately NOT setting torch.backends.cudnn.benchmark = True
        # here. It re-runs an autotuning search whenever a new input shape is
        # seen, and our inputs (description + prompt + however many tokens got
        # generated) have a *different* shape on nearly every call — so it was
        # paying a multi-second search cost repeatedly instead of amortizing it.

        repo = REPO_ID
        if not os.path.isdir(repo):
            # Local ModelScope/HF checkout missing — fall back to hub id.
            repo = os.environ.get("PARLER_HF_ID", "ai4bharat/indic-parler-tts")
        log.info("loading Indic Parler-TTS from %s on %s", repo, device)
        kw = {"token": HF_TOKEN} if HF_TOKEN else {}

        dtype = torch.float16 if device.startswith("cuda") else torch.float32
        if os.environ.get("PARLER_FP16", "1") != "1":
            dtype = torch.float32

        # sdpa uses PyTorch's fused scaled_dot_product_attention kernel, which
        # has a memory-efficient backend that works (and helps) on Turing (T4)
        # even without flash-attention-2 (Ampere+ only). This is a composite
        # model (text_encoder / audio_encoder / decoder sub-configs) and the
        # decoder is the autoregressive bottleneck run on every token, so
        # that's the one we most want on sdpa. Neither the T5 text_encoder nor
        # the DAC audio_encoder implement sdpa in this transformers version —
        # that's fine for text_encoder since we only run it once per voice at
        # startup (see _precompute_description_cache); audio_encoder (DAC) only
        # does the final waveform decode, not the per-token autoregressive loop.
        attn_impl = os.environ.get("PARLER_ATTN_IMPLEMENTATION", "sdpa")
        attn_map = {"text_encoder": "eager", "audio_encoder": "eager", "decoder": attn_impl}
        try:
            self._model = ParlerTTSForConditionalGeneration.from_pretrained(
                repo, torch_dtype=dtype, attn_implementation=attn_map, **kw
            ).to(device)
            log.info("parler loaded with attn_implementation=%s", attn_map)
        except Exception as exc:
            log.warning("attn_implementation=%s failed (%s); retrying with eager", attn_map, exc)
            self._model = ParlerTTSForConditionalGeneration.from_pretrained(
                repo, torch_dtype=dtype, **kw
            ).to(device)
        self._model.eval()
        self._prompt_tok = AutoTokenizer.from_pretrained(repo, **kw)
        desc_name = self._model.config.text_encoder._name_or_path
        self._desc_tok = AutoTokenizer.from_pretrained(desc_name, **kw)
        self._sample_rate = int(
            getattr(self._model.config, "sampling_rate", None)
            or getattr(getattr(self._model.config, "audio_encoder", None), "sampling_rate", 44100)
            or 44100
        )

        self._precompute_description_cache()

    def _precompute_description_cache(self) -> None:
        """Run the (large, Flan-T5) description text-encoder once per voice.

        The style/voice description is fixed per voice id — it never changes
        between calls — but ``model.generate()`` normally re-runs the full
        text-encoder forward pass on it every single synth. That's a ~780M
        parameter forward pass spent on text that is byte-for-byte identical
        every time. We compute it once here and cache the resulting
        ``last_hidden_state``; ``_stream_locked`` then passes it straight in
        as ``encoder_outputs=``, which makes ``generate()`` skip the
        text-encoder call entirely (see ``if "encoder_outputs" not in
        model_kwargs`` in parler_tts's ``generate``).
        """
        import torch

        self._desc_cache: dict[str, "torch.Tensor"] = {}
        device = self._device
        text_encoder = self._model.get_text_encoder()
        proj = getattr(self._model, "enc_to_dec_proj", None)
        with torch.inference_mode():
            for voice_id, info in self.voices.items():
                desc = self._desc_tok(info.description, return_tensors="pt").to(device)
                hidden = text_encoder(
                    input_ids=desc.input_ids,
                    attention_mask=desc.attention_mask,
                    return_dict=True,
                ).last_hidden_state
                if proj is not None:
                    hidden = proj(hidden)
                # attention_mask is all-ones for a single short, unpadded
                # description, so the mask-multiply in the stock code path is
                # a no-op here; skipped since we always encode one sequence.
                self._desc_cache[voice_id] = hidden
        log.info("parler description cache ready for %d voice(s)", len(self._desc_cache))

    def synthesize_pcm(self, voice_id: str, text: str) -> Iterator[bytes]:
        if voice_id not in self.voices:
            raise KeyError(voice_id)
        clean = " ".join((text or "").split())
        if not clean:
            return
        if self._model is None:
            raise RuntimeError("Indic Parler model not loaded")

        info = self.voices[voice_id]
        started = time.perf_counter()
        first_ms: float | None = None
        total = 0

        # Serialize GPU generate calls; streamer yields on another thread.
        with self._lock:
            if STREAM_PLAYBACK:
                for pcm in self._stream_locked(info, clean):
                    if first_ms is None:
                        first_ms = (time.perf_counter() - started) * 1000
                    total += len(pcm)
                    yield pcm
            else:
                # Buffer then emit so telephony never underruns between GPU chunks.
                for pcm in self._buffered_locked(info, clean):
                    if first_ms is None:
                        first_ms = (time.perf_counter() - started) * 1000
                    total += len(pcm)
                    yield pcm

        log.info(
            "parler synth total=%.0fms first=%.0fms voice=%s/%s chars=%d audio=%.2fs stream=%s",
            (time.perf_counter() - started) * 1000,
            first_ms or -1,
            voice_id,
            info.speaker,
            len(clean),
            total / 2 / TARGET_SR,
            STREAM_PLAYBACK,
        )

    def _buffered_locked(self, info: ParlerVoiceInfo, text: str) -> Iterator[bytes]:
        """Generate fully (or past jitter threshold), then emit without wall-clock gaps."""
        jitter_bytes = int(max(0.0, JITTER_BUFFER_S) * TARGET_SR * 2)
        buf = bytearray()
        released = False
        for pcm in self._stream_locked(info, text):
            buf.extend(pcm)
            if not released and jitter_bytes and len(buf) >= jitter_bytes:
                # Emit what we have as one continuous block, then stream the rest
                # only if generation can keep up — for T4 it usually can't, so
                # default jitter is 0 (full buffer). Non-zero is an escape hatch.
                yield bytes(buf)
                buf.clear()
                released = True
            elif released:
                yield pcm
        if buf:
            yield bytes(buf)

    def _stream_locked(self, info: ParlerVoiceInfo, text: str) -> Iterator[bytes]:
        import torch
        from parler_tts import ParlerTTSStreamer
        from transformers.modeling_outputs import BaseModelOutput

        model = self._model
        device = self._device
        frame_rate = model.audio_encoder.config.frame_rate
        play_steps = max(1, int(frame_rate * PLAY_STEPS_S))
        streamer = ParlerTTSStreamer(model, device=device, play_steps=play_steps, timeout=120.0)

        desc = self._desc_tok(info.description, return_tensors="pt").to(device)
        prompt = self._prompt_tok(text, return_tensors="pt").to(device)

        # Safety cap on generated length. Without this, `do_sample=True` has no
        # bound other than the model's own default (max_length=2610 tokens @
        # ~87Hz ≈ 30s!) — in testing this let a *single word* occasionally
        # generate ~4s of rambling audio (hallucinated continuation past EOS),
        # which both wastes latency and sounds unnatural. We bound max_new_tokens
        # to a generous multiple of the expected speaking time for the text so
        # legitimate longer clauses still have headroom, but runaway generation
        # gets cut off quickly instead of eating multiple extra seconds.
        words = max(1, len(text.split()))
        words_per_sec = float(os.environ.get("PARLER_WORDS_PER_SEC", "1.6"))
        cap_s = max(
            float(os.environ.get("PARLER_MIN_AUDIO_S", "1.2")),
            words / words_per_sec + float(os.environ.get("PARLER_AUDIO_PAD_S", "0.6")),
        )
        max_new_tokens = int(cap_s * frame_rate)

        gen_kwargs = dict(
            input_ids=desc.input_ids,
            attention_mask=desc.attention_mask,
            prompt_input_ids=prompt.input_ids,
            prompt_attention_mask=prompt.attention_mask,
            streamer=streamer,
            # Mild sampling — full temperature=1.0 was causing occasional glitches.
            do_sample=True,
            temperature=0.85,
            min_new_tokens=10,
            max_new_tokens=max_new_tokens,
        )
        cached_desc = getattr(self, "_desc_cache", {}).get(info.id)
        if cached_desc is not None:
            # Skip re-running the Flan-T5-large description encoder — it's
            # the same forward pass every single call since the description
            # text never changes per voice. ``input_ids``/``attention_mask``
            # above are still passed for batch-size/device bookkeeping only;
            # generate() short-circuits its own text-encoder call once
            # ``encoder_outputs`` is already present in kwargs.
            gen_kwargs["encoder_outputs"] = BaseModelOutput(last_hidden_state=cached_desc)

        # generate() pushes chunks into streamer; we iterate streamer in this thread.
        err: list[BaseException] = []

        def _run() -> None:
            try:
                with torch.inference_mode():
                    model.generate(**gen_kwargs)
            except BaseException as exc:  # noqa: BLE001 — surface to consumer
                err.append(exc)
                try:
                    streamer.end()
                except Exception:
                    pass

        worker = threading.Thread(target=_run, daemon=True, name="parler-generate")
        worker.start()

        gain = float(info.gain) * GAIN
        resampler = _StreamingResampler(self._sample_rate, TARGET_SR)
        xfade_n = max(0, int(TARGET_SR * CHUNK_XFADE_MS / 1000.0))
        prev_tail: np.ndarray | None = None

        try:
            for audio in streamer:
                if err:
                    raise err[0]
                if audio is None:
                    continue
                if hasattr(audio, "detach"):
                    audio = audio.detach().float().cpu().numpy()
                arr = np.asarray(audio, dtype=np.float32).reshape(-1)
                if arr.size == 0:
                    continue
                arr = resampler.push(arr)
                if arr.size == 0:
                    continue
                if gain != 1.0:
                    arr = arr * gain
                arr = np.clip(arr, -1.0, 1.0)
                if prev_tail is not None and xfade_n > 0 and arr.size >= xfade_n:
                    n = min(xfade_n, prev_tail.size, arr.size)
                    w = np.linspace(0.0, 1.0, n, dtype=np.float32)
                    arr[:n] = prev_tail[-n:] * (1.0 - w) + arr[:n] * w
                if xfade_n > 0 and arr.size > xfade_n:
                    # Hold last samples to crossfade into the next chunk; emit the rest now.
                    emit, prev_tail = arr[:-xfade_n], arr[-xfade_n:].copy()
                else:
                    emit, prev_tail = arr, None
                if emit.size:
                    yield (emit * 32767.0).astype(np.int16).tobytes()
            # Flush residual resample input + held crossfade tail.
            tail = resampler.flush()
            if tail.size:
                if gain != 1.0:
                    tail = tail * gain
                tail = np.clip(tail, -1.0, 1.0)
                if prev_tail is not None and xfade_n > 0 and tail.size >= 1:
                    n = min(xfade_n, prev_tail.size, tail.size)
                    w = np.linspace(0.0, 1.0, n, dtype=np.float32)
                    tail[:n] = prev_tail[-n:] * (1.0 - w) + tail[:n] * w
                    prev_tail = None
                yield (tail * 32767.0).astype(np.int16).tobytes()
            elif prev_tail is not None and prev_tail.size:
                yield (np.clip(prev_tail, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
        finally:
            worker.join(timeout=120.0)
            if err:
                raise err[0]


class _StreamingResampler:
    """Continuous linear resampler so chunk boundaries don't click."""

    def __init__(self, src: int, dst: int) -> None:
        self.src = int(src)
        self.dst = int(dst)
        self._pos = 0.0  # next output sample position in source-sample units
        self._buf = np.zeros(0, dtype=np.float32)

    def push(self, samples: np.ndarray) -> np.ndarray:
        if self.src == self.dst:
            return samples.astype(np.float32, copy=False)
        if samples.size == 0:
            return np.zeros(0, dtype=np.float32)
        self._buf = np.concatenate([self._buf, samples.astype(np.float32, copy=False)])
        return self._emit(final=False)

    def flush(self) -> np.ndarray:
        if self.src == self.dst:
            return np.zeros(0, dtype=np.float32)
        return self._emit(final=True)

    def _emit(self, *, final: bool) -> np.ndarray:
        if self._buf.size < 2:
            return np.zeros(0, dtype=np.float32)
        step = self.src / float(self.dst)
        # Need one sample of look-ahead for linear interp unless flushing.
        max_pos = (self._buf.size - 1) if final else (self._buf.size - 2)
        if max_pos < self._pos:
            return np.zeros(0, dtype=np.float32)
        n = int(np.floor((max_pos - self._pos) / step)) + 1
        if n <= 0:
            return np.zeros(0, dtype=np.float32)
        positions = self._pos + step * np.arange(n, dtype=np.float64)
        i0 = np.floor(positions).astype(np.int64)
        frac = (positions - i0).astype(np.float32)
        i0 = np.clip(i0, 0, self._buf.size - 2)
        out = self._buf[i0] * (1.0 - frac) + self._buf[i0 + 1] * frac
        self._pos = float(positions[-1] + step)
        # Drop consumed source samples (keep 1 for continuity).
        drop = int(np.floor(self._pos))
        if drop > 0:
            drop = min(drop, max(0, self._buf.size - 1))
            self._buf = self._buf[drop:]
            self._pos -= drop
        return out.astype(np.float32)
