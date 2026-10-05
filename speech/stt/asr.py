"""Sherpa-onnx online ASR + Silero VAD + optional smart-turn classifier."""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger("speech_stt.asr")

MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/models"))
STT_DIR = Path(os.environ.get("STT_MODEL_DIR", MODELS_DIR / "stt" / "nemotron"))
SMART_TURN_PATH = Path(
    os.environ.get(
        "SMART_TURN_PATH",
        MODELS_DIR / "stt" / "smart-turn" / "smart-turn-v3-gpu.onnx",
    )
)
PROVIDER = os.environ.get("SHERPA_PROVIDER", "cuda")  # cuda | cpu
NUM_THREADS = int(os.environ.get("SHERPA_NUM_THREADS", "2"))
SAMPLE_RATE = 16000


@dataclass
class StreamHandle:
    stream: Any
    language: str = "auto"
    vad: Any = None  # per-stream Silero VAD; never share across calls


class AsrEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.recognizer = None
        self._vad_config = None  # template; each stream gets its own detector
        self.smart_turn = None
        self._load()

    def _load(self) -> None:
        try:
            import sherpa_onnx
        except ImportError as exc:
            raise RuntimeError("sherpa-onnx is required in the speech-stt image") from exc

        encoder = STT_DIR / "encoder.int8.onnx"
        if not encoder.exists():
            encoder = STT_DIR / "encoder.onnx"
        decoder = STT_DIR / "decoder.int8.onnx"
        if not decoder.exists():
            decoder = STT_DIR / "decoder.onnx"
        joiner = STT_DIR / "joiner.int8.onnx"
        if not joiner.exists():
            joiner = STT_DIR / "joiner.onnx"
        tokens = STT_DIR / "tokens.txt"
        missing = [p for p in (encoder, decoder, joiner, tokens) if not p.exists()]
        if missing:
            raise FileNotFoundError(
                f"STT model incomplete under {STT_DIR}; missing {[str(p) for p in missing]}. "
                "Run the speech-models Compose job first."
            )

        log.info("loading sherpa transducer from %s provider=%s", STT_DIR, PROVIDER)
        self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(tokens),
            encoder=str(encoder),
            decoder=str(decoder),
            joiner=str(joiner),
            num_threads=NUM_THREADS,
            sample_rate=SAMPLE_RATE,
            feature_dim=80,
            decoding_method="greedy_search",
            provider=PROVIDER,
            model_type="nemo_transducer",
        )

        # Silero VAD shipped with sherpa-onnx releases; optional path override.
        vad_model = Path(os.environ.get("SILERO_VAD_PATH", MODELS_DIR / "stt" / "silero_vad.onnx"))
        if not vad_model.exists():
            # Try common sherpa bundled location inside the model tree.
            for candidate in STT_DIR.rglob("silero_vad.onnx"):
                vad_model = candidate
                break
        if vad_model.exists():
            vad_config = sherpa_onnx.VadModelConfig()
            vad_config.silero_vad.model = str(vad_model)
            vad_config.silero_vad.min_silence_duration = 0.15
            vad_config.silero_vad.min_speech_duration = 0.1
            vad_config.sample_rate = SAMPLE_RATE
            self._vad_config = vad_config
            log.info("silero VAD loaded from %s", vad_model)
        else:
            log.warning("silero VAD model not found; using energy VAD fallback")

        self.smart_turn = _maybe_load_smart_turn(SMART_TURN_PATH)

    def _new_vad(self):
        if self._vad_config is None:
            return None
        import sherpa_onnx

        return sherpa_onnx.VoiceActivityDetector(self._vad_config, buffer_size_in_seconds=30)

    def create_stream(self, language: str = "auto") -> StreamHandle:
        stream = self.recognizer.create_stream()
        # Nemotron prompt language: empty/auto for code-switch, en/hi when pinned.
        lang = (language or "auto").lower()
        if lang in ("", "multi", "auto", "hi", "hinglish"):
            prompt = "auto" if lang != "en" else "en"
        elif lang.startswith("en"):
            prompt = "en"
        else:
            prompt = "auto"
        set_opt = getattr(stream, "set_option", None) or getattr(stream, "SetOption", None)
        if callable(set_opt):
            try:
                set_opt("language", prompt)
            except Exception as exc:
                log.debug("stream language option unsupported: %s", exc)
        return StreamHandle(stream=stream, language=prompt, vad=self._new_vad())

    def accept_pcm16(self, handle: StreamHandle, pcm16: bytes, input_rate: int) -> None:
        audio = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
        if input_rate != SAMPLE_RATE and len(audio):
            audio = _resample(audio, input_rate, SAMPLE_RATE)
        with self._lock:
            handle.stream.accept_waveform(SAMPLE_RATE, audio)

    def decode_batch(self, handles: list[StreamHandle]) -> list[str]:
        if not handles:
            return []
        with self._lock:
            ready = [h.stream for h in handles if self.recognizer.is_ready(h.stream)]
            if ready:
                self.recognizer.decode_streams(ready)
            # This sherpa-onnx build's get_result() returns the transcript as
            # a plain str, not an object with a `.text` attribute. Calling
            # `.text` raised "'str' object has no attribute 'text'" on every
            # tick, which aborted _drain_session before the turn state
            # machine ever ran -- no StartOfTurn/Update/EndOfTurn was ever
            # emitted, so the agent could never hear or respond to a caller.
            return [self.recognizer.get_result(h.stream).strip() for h in handles]

    def is_speech(self, handle: StreamHandle, pcm16: bytes, input_rate: int) -> bool:
        """Return whether *this* stream is currently in speech.

        Important: Silero's ``empty()`` means "no *finished* speech segments
        queued" — once a segment is finalized it stays queued until ``pop()``,
        so treating ``not empty()`` as live speech sticks ``is_speech=True``
        forever after the first utterance and we never emit EndOfTurn. Dograh
        Flux needs EndOfTurn to commit the user turn to the LLM; without it
        the call just sits until user_idle hangup even though Updates had text.
        Use ``is_speech_detected()`` for the live flag, and drain finished
        segments so the queue does not grow.
        """
        audio = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
        if input_rate != SAMPLE_RATE and len(audio):
            audio = _resample(audio, input_rate, SAMPLE_RATE)
        vad = handle.vad
        if vad is not None:
            with self._lock:
                vad.accept_waveform(audio)
                while not vad.empty():
                    vad.pop()
                speaking = bool(vad.is_speech_detected())
            # Telephony echo of the bot is usually quieter than near-end speech.
            # Require a modest energy floor even when Silero flips true, so the
            # bot's own playback on the line does not become a fake user turn.
            if speaking:
                mean_abs = float(np.abs(audio).mean()) if len(audio) else 0.0
                speaking = mean_abs >= float(os.environ.get("STT_SPEECH_MIN_ABS", "0.012"))
            return speaking
        # Energy fallback
        if not len(audio):
            return False
        rms = float(np.sqrt(np.mean(audio * audio)))
        return rms > float(os.environ.get("STT_SPEECH_MIN_RMS", "0.018"))

    def end_of_turn_prob(self, pcm16_window: bytes, input_rate: int) -> float | None:
        if self.smart_turn is None:
            return None
        audio = np.frombuffer(pcm16_window, dtype=np.int16).astype(np.float32) / 32768.0
        if input_rate != SAMPLE_RATE and len(audio):
            audio = _resample(audio, input_rate, SAMPLE_RATE)
        try:
            return float(self.smart_turn(audio))
        except Exception as exc:
            log.debug("smart-turn failed: %s", exc)
            return None


def _resample(audio: np.ndarray, src: int, dst: int) -> np.ndarray:
    if src == dst or len(audio) == 0:
        return audio
    duration = len(audio) / float(src)
    n = max(1, int(duration * dst))
    x_old = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=n, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)


def _maybe_load_smart_turn(path: Path):
    if not path.exists():
        cpu = path.parent / "smart-turn-v3-cpu.onnx"
        path = cpu if cpu.exists() else path
    if not path.exists():
        log.warning("smart-turn model missing at %s", path)
        return None
    try:
        import onnxruntime as ort
    except ImportError:
        log.warning("onnxruntime not installed; smart-turn disabled")
        return None

    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    try:
        session = ort.InferenceSession(str(path), providers=providers)
    except Exception:
        session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])

    input_name = session.get_inputs()[0].name

    def predict(audio_f32: np.ndarray) -> float:
        # Smart-turn expects ~8s mono 16 kHz; pad/trim.
        target = SAMPLE_RATE * 8
        if len(audio_f32) < target:
            audio_f32 = np.pad(audio_f32, (0, target - len(audio_f32)))
        else:
            audio_f32 = audio_f32[-target:]
        arr = audio_f32.astype(np.float32)[None, :]
        out = session.run(None, {input_name: arr})[0]
        # Output shape varies; take last scalar probability.
        val = np.asarray(out).reshape(-1)[-1]
        return float(val)

    log.info("smart-turn loaded from %s", path)
    return predict
