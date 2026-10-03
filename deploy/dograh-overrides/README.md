# Dograh base model configuration

Do not paste JSON into Dograh's UI for the shared org. From the app machine:

```bash
docker compose -f deploy/docker-compose.yml exec backend python manage.py bootstrap_dograh
```

That command sets:

- **LLM** → `http://context-guard:8080/v1`
- **STT** → `http://speech-stt:8000` (Deepgram Flux protocol, Nemotron Hinglish)
- **TTS** → `http://speech-tts:8000/v1` (OpenAI speech API, dhee-indic-f5)

Per-campaign language and voice presets are applied automatically when an agent is published (`apps/agents/model_overrides.py`).
