# Maya 2 Native TTS

Self-hosted [Maya 2 Native](https://huggingface.co/maya-research/maya2-native) is the
production TTS engine for this stack. Campaigns, Dograh, STT, and telephony stay the same.

## Layout

| Piece | Role |
|-------|------|
| `maya-tts-api` | GPU server (`python -m maya3.server`), original Maya preset voices |
| `maya-tts-proxy` | OpenAI `/v1` facade: maps `hi_female` / `hi_male_hinglish` / … → Maya voice + language |
| `runtime/venv` | maya3 install (local, gitignored — created by `install-venv.sh`) |
| `hf-cache` | Hugging Face weights cache (local, gitignored) |

## Voice mapping (proxy defaults)

| Campaign model id | Maya voice | Language |
|-------------------|------------|----------|
| `hi_female`, `hi_female_hinglish` | Ahana | hi |
| `hi_male`, `hi_male_hinglish` | Ritvik | hi |
| `en_female` | Tanushree | en |
| `en_male` | Siddhant | en |

Voice and language are independent in Maya; the table is only our campaign pairing.
Override with `MAYA_VOICE_FEMALE` / `MAYA_VOICE_MALE` / `MAYA_VOICE_EN_*` in compose.

## Bring up

```bash
# From interaction_bot/
./deploy/switch-tts.sh maya
```

That installs the venv if needed, starts Maya + proxy, points `SPEECH_TTS_URL` and
Dograh's TTS provider connection at `http://maya-tts-proxy:8080/v1`, and applies
`deploy/maya.host.yml`.

## Notes

- Triton fused kernels segfault on some hosts; `patch_engine.py` + `patch_triton_fallback.py`
  force eager PyTorch paths. Re-applied by `install-venv.sh`.
- `/v1/audio/prewarm` is implemented on the proxy (best-effort).
- Dograh v3 stores TTS `base_url` on `provider_connections` — `switch-tts.sh` patches
  both that and the legacy `MODEL_CONFIGURATION_V2` blob.
