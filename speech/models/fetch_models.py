#!/usr/bin/env python3
"""Download and prepare self-hosted STT/TTS model assets into MODELS_DIR.

Idempotent: skips work when the manifest matches. Run inside the speech-models
Compose job (or locally with a Hugging Face token for gated repos).

  MODELS_DIR=/models python speech/models/fetch_models.py
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import wave
from pathlib import Path

MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/models"))
HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or ""
MANIFEST_PATH = MODELS_DIR / "manifest.json"

# Prefer the Hinglish fine-tune; fall back to NVIDIA's multilingual streaming
# sherpa-onnx package when NeMo export is unavailable.
NEMOTRON_HF = os.environ.get("NEMOTRON_HF_ID", "smajji/nemotron-hinglish-v2")
SHERPA_FALLBACK_URL = os.environ.get(
    "SHERPA_NEMOTRON_URL",
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-560ms-int8-2026-06-11.tar.bz2",
)
DHEE_HF = os.environ.get("DHEE_HF_ID", "dheeyantra/dhee-indic-f5")
SMART_TURN_URL = os.environ.get(
    "SMART_TURN_URL",
    "https://huggingface.co/pipecat-ai/smart-turn-v3/resolve/main/smart-turn-v3.2-cpu.onnx",
)
SMART_TURN_GPU_URL = os.environ.get(
    "SMART_TURN_GPU_URL",
    "https://huggingface.co/pipecat-ai/smart-turn-v3/resolve/main/smart-turn-v3.2-gpu.onnx",
)
SILERO_VAD_URL = os.environ.get(
    "SILERO_VAD_URL",
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx",
)
# AI4Bharat Indic-TTS FastPitch+HiFi-GAN Hindi checkpoint (~1.4GB zip).
INDIC_TTS_ZIP_URL = os.environ.get(
    "INDIC_TTS_ZIP_URL",
    "https://github.com/AI4Bharat/Indic-TTS/releases/download/"
    "v1-checkpoints-release/hi.zip",
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path, headers: dict | None = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers=headers or {})
    print(f"download {url} -> {dest}")
    with urllib.request.urlopen(req, timeout=600) as resp, tmp.open("wb") as out:
        shutil.copyfileobj(resp, out)
    tmp.replace(dest)


def _hf_snapshot(repo_id: str, local_dir: Path) -> None:
    from huggingface_hub import snapshot_download

    kwargs = {"repo_id": repo_id, "local_dir": str(local_dir)}
    if HF_TOKEN:
        kwargs["token"] = HF_TOKEN
    print(f"hf snapshot {repo_id} -> {local_dir}")
    snapshot_download(**kwargs)


def _write_silence_wav(path: Path, seconds: float = 6.0, sr: int = 24000) -> None:
    """Placeholder reference clip until a consented voice is recorded."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(seconds * sr)
    # Soft 220 Hz tone so the file is non-silent (F5/IndicF5 need energy).
    import math
    import struct

    frames = bytearray()
    for i in range(n):
        t = i / sr
        # Fade in/out envelope
        env = min(1.0, t * 4) * min(1.0, (seconds - t) * 4)
        sample = int(0.15 * env * math.sin(2 * math.pi * 220 * t) * 32767)
        frames.extend(struct.pack("<h", sample))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(bytes(frames))


def _patch_dhee_forward_nfe_step(dest: Path) -> None:
    """dheeyantra/dhee-indic-f5's model.py forward() doesn't accept nfe_step,
    so infer_process/infer_batch_process silently default to 32 diffusion
    steps regardless of TTS_NFE, doubling synthesis latency for no configured
    reason. Patch it once, idempotently, so engine.py's nfe_step=NFE actually
    takes effect.
    """
    model_py = dest / "model.py"
    if not model_py.exists():
        return
    content = model_py.read_text(encoding="utf-8")
    if "nfe_step" in content:
        return  # already patched (or upstream added support itself)
    old_sig = 'def forward(self, text: str, ref_audio_path: str, ref_text: str):'
    old_call_tail = (
        '            mel_spec_type="vocos",\n'
        "            speed=self.config.speed,\n"
        "            device=self.device,\n"
        "        )"
    )
    new_call_tail = (
        '            mel_spec_type="vocos",\n'
        "            speed=self.config.speed,\n"
        "            device=self.device,\n"
        "            **({\"nfe_step\": nfe_step} if nfe_step is not None else {}),\n"
        "        )"
    )
    if old_sig not in content or old_call_tail not in content:
        print("WARNING: dhee-indic-f5 model.py shape changed; nfe_step patch skipped")
        return
    content = content.replace(
        old_sig,
        "def forward(self, text: str, ref_audio_path: str, ref_text: str, nfe_step: int = None):",
        1,
    )
    content = content.replace(old_call_tail, new_call_tail, 1)
    model_py.write_text(content, encoding="utf-8")
    print(f"patched {model_py} to forward nfe_step")


def fetch_tts() -> dict:
    dest = MODELS_DIR / "tts" / "dhee-indic-f5"
    if not (dest / "config.json").exists() and not any(dest.glob("*.safetensors")):
        dest.mkdir(parents=True, exist_ok=True)
        try:
            _hf_snapshot(DHEE_HF, dest)
        except Exception as exc:
            print(f"WARNING: dhee-indic-f5 download failed ({exc}); TTS image will pull on first start")
    _patch_dhee_forward_nfe_step(dest)
    # Four system voices (Hindi/English × female/male). Prefer checked-in
    # samples from speech/data_for_voice or speech/tts/voices, then fall back
    # to short placeholder tones only if nothing is present.
    voices = MODELS_DIR / "tts" / "voices"
    voices.mkdir(parents=True, exist_ok=True)
    repo_roots = [
        Path(__file__).resolve().parents[1] / "data_for_voice",
        Path(__file__).resolve().parents[1] / "tts" / "voices",
        Path("/app/data_for_voice"),
        Path("/app/voices"),
    ]
    presets = [
        ("hi_female.wav", "hi_female.txt", "नमस्ते, मैं आपकी सहायता के लिए यहाँ हूँ।"),
        ("hi_male.wav", "hi_male.txt", "नमस्ते, मैं आपकी सहायता के लिए यहाँ हूँ।"),
        ("en_female.wav", "en_female.txt", "Hello, I am here to help you."),
        ("en_male.wav", "en_male.txt", "Hello, I am here to help you."),
    ]
    for wav_name, txt_name, transcript in presets:
        wav = voices / wav_name
        txt = voices / txt_name
        src_wav = next((root / wav_name for root in repo_roots if (root / wav_name).exists()), None)
        src_txt = next((root / txt_name for root in repo_roots if (root / txt_name).exists()), None)
        if src_wav and (not wav.exists() or wav.stat().st_size < src_wav.stat().st_size):
            shutil.copy2(src_wav, wav)
            print(f"voice sample {wav_name} <- {src_wav}")
        if src_txt:
            shutil.copy2(src_txt, txt)
        if not wav.exists():
            _write_silence_wav(wav)
            txt.write_text(transcript, encoding="utf-8")
            print(f"WARNING: placeholder tone written for {wav_name}")
    return {"tts_repo": DHEE_HF, "tts_dir": str(dest)}


def fetch_indic_vits() -> dict:
    """Download Hindi VITS checkpoints fine-tuned on the IndicTTS speakers."""
    dest = MODELS_DIR / "tts" / "indic-vits"
    repos = {
        "female": os.environ.get("INDIC_VITS_FEMALE_REPO", "onecxi/mms-hindi-female-indic"),
        "male": os.environ.get("INDIC_VITS_MALE_REPO", "onecxi/mms-hindi-male-indic"),
    }
    got = {}
    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:
        print(f"WARNING: IndicTTS VITS download skipped ({exc})")
        return {"indic_vits_dir": str(dest), "source": "missing"}
    for speaker, repo in repos.items():
        folder = dest / speaker
        marker = folder / "model.safetensors"
        if marker.exists() and marker.stat().st_size > 10_000_000:
            got[speaker] = "existing"
            continue
        try:
            print(f"fetching IndicTTS VITS {speaker} from {repo} -> {folder}")
            snapshot_download(repo, local_dir=str(folder))
            got[speaker] = "huggingface" if marker.exists() else "missing"
        except Exception as exc:
            print(f"WARNING: IndicTTS VITS {speaker} download failed ({exc})")
            got[speaker] = "missing"
    return {"indic_vits_dir": str(dest), "voices": got}


def fetch_indic_tts() -> dict:
    """Download AI4Bharat Hindi FastPitch + HiFi-GAN checkpoints."""
    import zipfile

    dest = MODELS_DIR / "tts" / "indic-tts"
    marker = dest / "hi" / "fastpitch" / "best_model.pth"
    nested = dest / "hi" / "hi" / "fastpitch" / "best_model.pth"
    if marker.exists() or nested.exists():
        _patch_indic_tts_speakers_paths(dest)
        return {"indic_tts_dir": str(dest), "source": "existing"}

    dest.mkdir(parents=True, exist_ok=True)
    archive = MODELS_DIR / "tts" / "indic-tts-hi.zip"
    try:
        if not archive.exists() or archive.stat().st_size < 1_000_000:
            _download(INDIC_TTS_ZIP_URL, archive)
        print(f"unpacking Indic-TTS Hindi -> {dest}")
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(dest)
        # Normalize accidental hi/hi nesting from some zip layouts.
        if nested.exists() and not marker.exists():
            inner = dest / "hi" / "hi"
            outer = dest / "hi"
            for child in inner.iterdir():
                target = outer / child.name
                if not target.exists():
                    child.rename(target)
        if marker.exists() or nested.exists():
            _patch_indic_tts_speakers_paths(dest)
            return {"indic_tts_dir": str(dest), "source": "github-release"}
    except Exception as exc:
        print(f"WARNING: Indic-TTS download failed ({exc})")
    return {"indic_tts_dir": str(dest), "source": "missing"}


def _patch_indic_tts_speakers_paths(dest: Path) -> None:
    """Rewrite training-time speakers_file paths to the live volume location."""
    hi = dest / "hi"
    if (hi / "hi" / "fastpitch" / "speakers.pth").exists() and not (
        hi / "fastpitch" / "speakers.pth"
    ).exists():
        hi = hi / "hi"
    spk = hi / "fastpitch" / "speakers.pth"
    if not spk.exists():
        return
    # Prefer the in-container absolute path the TTS service mounts.
    spk_path = f"/models/tts/indic-tts/hi/fastpitch/speakers.pth"
    for cfg in (hi / "config.json", hi / "fastpitch" / "config.json"):
        if not cfg.exists():
            continue
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except Exception:
            continue
        data["speakers_file"] = spk_path
        if isinstance(data.get("model_args"), dict):
            data["model_args"]["speakers_file"] = spk_path
        cfg.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
        print(f"patched speakers_file in {cfg}")
    # Ensure top-level config.json exists (Coqui often expects it).
    top = hi / "config.json"
    fp_cfg = hi / "fastpitch" / "config.json"
    if not top.exists() and fp_cfg.exists():
        shutil.copy2(fp_cfg, top)


def fetch_silero_vad() -> dict:
    dest = MODELS_DIR / "stt" / "silero_vad.onnx"
    if not dest.exists():
        try:
            _download(SILERO_VAD_URL, dest)
        except Exception as exc:
            print(f"WARNING: silero vad download failed: {exc}")
    return {"silero_vad": str(dest)}


def fetch_smart_turn() -> dict:
    dest = MODELS_DIR / "stt" / "smart-turn"
    dest.mkdir(parents=True, exist_ok=True)
    cpu = dest / "smart-turn-v3-cpu.onnx"
    gpu = dest / "smart-turn-v3-gpu.onnx"
    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"
    if not cpu.exists():
        try:
            _download(SMART_TURN_URL, cpu, headers=headers)
        except Exception as exc:
            print(f"WARNING: smart-turn cpu download failed: {exc}")
    if not gpu.exists():
        try:
            _download(SMART_TURN_GPU_URL, gpu, headers=headers)
        except Exception as exc:
            print(f"WARNING: smart-turn gpu download failed: {exc}")
    return {"smart_turn_dir": str(dest)}


def export_nemotron_or_fallback() -> dict:
    """Export Nemotron Hinglish to sherpa-onnx, or unpack the multilingual fallback."""
    out = MODELS_DIR / "stt" / "nemotron"
    marker = out / "tokens.txt"
    if marker.exists():
        return {"stt_dir": str(out), "source": "existing"}

    out.mkdir(parents=True, exist_ok=True)
    export_script = Path(__file__).with_name("export_nemotron.sh")
    if export_script.exists() and os.environ.get("SKIP_NEMOTRON_EXPORT") != "1":
        try:
            print(f"exporting {NEMOTRON_HF} via {export_script}")
            subprocess.run(
                ["bash", str(export_script), NEMOTRON_HF, str(out)],
                check=True,
            )
            if marker.exists():
                return {"stt_dir": str(out), "source": NEMOTRON_HF}
        except Exception as exc:
            print(f"WARNING: NeMo export failed ({exc}); using sherpa fallback package")

    archive = MODELS_DIR / "stt" / "nemotron-fallback.tar.bz2"
    if not archive.exists():
        _download(SHERPA_FALLBACK_URL, archive)
    with tarfile.open(archive, "r:bz2") as tar:
        tar.extractall(path=out.parent)
    # Flatten: find the extracted directory containing tokens.txt
    candidates = list(out.parent.glob("sherpa-onnx-nemotron*"))
    if candidates and not marker.exists():
        extracted = candidates[0]
        if extracted.resolve() != out.resolve():
            if out.exists():
                shutil.rmtree(out)
            extracted.rename(out)
    if not marker.exists():
        raise RuntimeError(f"STT model not ready under {out}")
    return {"stt_dir": str(out), "source": "sherpa-fallback"}


def main() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    info = {
        "tts": fetch_tts(),
        "indic_vits": fetch_indic_vits(),
        "indic_tts": fetch_indic_tts(),
        "smart_turn": fetch_smart_turn(),
        "silero_vad": fetch_silero_vad(),
        "stt": export_nemotron_or_fallback(),
    }
    MANIFEST_PATH.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(info, indent=2))
    print(f"manifest written to {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
