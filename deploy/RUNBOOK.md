# Deploying (self-hosted speech on GPU)

One GPU machine (~24GB VRAM), with a public IP. Speech-to-text is **Nemotron Hinglish** behind a Deepgram-Flux-compatible WebSocket (`speech-stt`). Voice is **dhee-indic-f5** behind an OpenAI-compatible speech API (`speech-tts`). The language model stays a hosted API (OpenAI `gpt-4o-mini` by default) behind the context guard.

```text
Internet
  |  443 (dashboard and webhooks)
  v
GPU host
  Caddy, Django, Celery, Postgres, Redis, Next.js
  Plivo  (outbound phone calls)
  context guard  (private, calls OpenAI)
  speech-stt     (GPU, Nemotron Hinglish, Flux protocol)
  speech-tts     (GPU, dhee-indic-f5, OpenAI speech API)
  Dograh (its own compose, joined to the Docker network named "caller")
        |
        +--> speech-stt / speech-tts on the caller network
        +--> Plivo, WhatsApp messages, upstream LLM
```

`/internal/` on Django is not published by Caddy. The context guard calls Django at `http://backend:8000` on the Docker network.

**Licence note:** `dheeyantra/dhee-indic-f5` is CC-BY-NC-4.0. Commercial use needs a licence from DheeYantra.

## 0. GPU host prerequisites

```bash
# NVIDIA driver + Container Toolkit (Ubuntu example)
nvidia-smi   # driver must work on the host
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
# Smoke-test GPU inside Docker:
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

## 1. App + speech models

```bash
cp .env.example .env
```

Replace `DJANGO_SECRET_KEY`, `FERNET_KEY`, `INTERNAL_API_TOKEN`, and `DOGRAH_WEBHOOK_SECRET`. Generate the first two with:

```bash
python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

Set `UPSTREAM_LLM_API_KEY`. Optionally set `HF_TOKEN` for Hugging Face downloads and `SPEECH_API_TOKEN` if you want the speech containers to require auth. Point `APP_DOMAIN` at the hostname that has an A record to this machine.

Fetch models into the shared Docker volume (one-shot):

```bash
docker compose -f deploy/docker-compose.yml --profile models run --rm speech-models
```

System voices ship from `speech/data_for_voice/` / `speech/tts/voices/`
(24 kHz, ~8s clips). The speech-models job copies them into the volume.
These are fixed Female/Male Indian-accent refs — not per-call user cloning.

Bring the stack up:

```bash
docker compose -f deploy/docker-compose.yml up --build -d
```

Caddy fetches a certificate for `APP_DOMAIN`. Confirm speech health:

```bash
docker compose -f deploy/docker-compose.yml exec speech-stt \
  python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read())"
docker compose -f deploy/docker-compose.yml exec speech-tts \
  python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read())"
```

Optional latency bench (from a host that can reach the services):

```bash
pip install httpx websockets
SPEECH_STT_URL=http://127.0.0.1:STT_PORT SPEECH_TTS_URL=http://127.0.0.1:TTS_PORT/v1 \
  python speech/bench/bench.py --concurrency 1 4
```

Targets: STT EndOfTurn p50 ≤ 450ms after speech ends; TTS first audio p50 ≤ 250ms; TTS RTF ≤ 0.15.

## 2. Dograh and Plivo

From the Dograh checkout (`./scripts/fetch_dograh.sh`):

```bash
docker compose -f docker-compose.yaml -f ../AI_Caller/deploy/dograh.override.yml up -d
```

The override puts Dograh on the `caller` network. Run the base model configuration once:

```bash
docker compose -f deploy/docker-compose.yml exec backend python manage.py bootstrap_dograh
```

This points Dograh at `http://context-guard:8080/v1` for the LLM, `http://speech-stt:8000` for Flux-compatible STT, and `http://speech-tts:8000/v1` for TTS. Republish every campaign agent so workflow overrides pick up the new presets.

Calls go out through Plivo. In Setup, Calling, save the Plivo Auth ID, Auth Token, and the caller ID. A WhatsApp reply is the customer's consent to be called. The agent then dials that mobile through Plivo, only between 09:00 and 21:00 IST. `STOP` opts the number out. The limit is 5 calls per person in 24 hours.

## 3. WhatsApp

In Meta, the callback URL is:

```text
https://APP_DOMAIN/webhooks/whatsapp/<business-slug>/
```

The verify token is generated when the business signs up and is shown on the Setup page. Subscribe to the `messages` field.

When the business sends a template, record the outbound message id so a reply can be matched to the campaign:

```text
POST /api/campaigns/<id>/outbound-messages/
{"wa_message_id": "wamid....", "phone": "+9198..."}
```

A reply button can also carry the payload `campaign:<campaign uuid>`. Otherwise a keyword, then the default campaign, is used.

## 4. What the agent is allowed to say

Campaign context is structured: offer, prices, FAQs, allowed topics, forbidden topics, competitors, and the handoff sentence. The context guard replaces Dograh's system prompt with the compiled one on every turn, forces temperature 0.2, and checks each sentence before it is returned. A sentence is replaced with the handoff line when it contains a number that is not in the facts, a forbidden topic, a competitor, or a script other than Devanagari or Latin. The red-team tests in `context_guard/tests/test_redteam.py` fail the build if that check regresses.

## 5. Tuning

| Env | Default | Effect |
|-----|---------|--------|
| `STT_EOT_SILENCE_MS` | 300 | Silence before EndOfTurn when smart-turn agrees |
| `STT_EAGER_SILENCE_MS` | 200 | Silence before EagerEndOfTurn |
| `STT_EOT_TIMEOUT_MS` | 1200 | Hard silence cap |
| `TTS_NFE` | 16 | Diffusion steps (lower = faster, lower quality) |
| `TTS_FIRST_CLAUSE_WORDS` | 8 | First spoken clause length for TTFB |
| `SPEECH_VOICE_NAME` | siya | Gender lock for Hindi prompts |
